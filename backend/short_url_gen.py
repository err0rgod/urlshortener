from sonyflake import SonyFlake
from datetime import datetime , UTC, timedelta
from base62 import encode_base62
from models import urldata
from database import add_to_db, get_long_url, is_long_url_exists, mark_url_banned, is_alias_exists
import redis
from logger import logger
# from validations import check_safe_browsing

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True,
    socket_connect_timeout=0.1,
    socket_timeout=0.1
)




custom_epoch = datetime(2014, 9, 1, 0, 0, 0, tzinfo=UTC)

generator =  SonyFlake(custom_epoch)



def get_short_url() -> str:
    unique_id = get_unique_id()
    short_url = encode_base62(unique_id)
    return short_url

def get_unique_id() -> str:
    return generator.next_id()


from typing import Optional

def add_url(
    long_url : str, 
    user_id: Optional[int] = None, 
    exp_time : Optional[int | datetime] = None,
    webhook_url: Optional[str] = None,
    ios_url: Optional[str] = None,
    android_url: Optional[str] = None,
    password_hash: Optional[str] = None,
    fallback_url: Optional[str] = None
):
    exists = is_long_url_exists(long_url, user_id=user_id)
    if exists:
        return exists
    db_exp_time = None
    if isinstance(exp_time, datetime):
        db_exp_time = exp_time.astimezone(UTC).replace(tzinfo=None) if exp_time.tzinfo else exp_time
    elif isinstance(exp_time, int):
        db_exp_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=exp_time)
    short_url = get_short_url()
    url = urldata(
        short_url=short_url,
        long_url=long_url,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        click_count=0,
        user_id=user_id,
        exp_time=db_exp_time,
        webhook_url=webhook_url,
        ios_url=ios_url,
        android_url=android_url,
        password_hash=password_hash,
        fallback_url=fallback_url
    )
    
    # Calculate correct Redis cache TTL
    redis_ttl = 3600
    is_expired = False
    if db_exp_time:
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        seconds_left = int((db_exp_time - now_naive).total_seconds())
        if seconds_left <= 0:
            is_expired = True
        else:
            redis_ttl = min(3600, seconds_left)

    is_dynamic = bool(webhook_url or ios_url or android_url or password_hash or fallback_url)

    try:
        if is_expired:
            redis_client.set(short_url, "Expired", ex=3600)
        elif is_dynamic:
            redis_client.set(short_url, "DYNAMIC", ex=3600)
        else:
            redis_client.set(short_url, long_url, ex=redis_ttl)
    except Exception as re:
        logger.warning(f"Redis is Offline falling back to Database: {re}")
    add_to_db(url)
    return short_url


def add_custom_url(
    long_url, 
    custom_alias, 
    user_id: Optional[int] = None, 
    exp_time : Optional[int | datetime] = None,
    webhook_url: Optional[str] = None,
    ios_url: Optional[str] = None,
    android_url: Optional[str] = None,
    password_hash: Optional[str] = None,
    fallback_url: Optional[str] = None
):
    does_exists = is_alias_exists(custom_alias)
    if does_exists:
        return None
    else:
        db_exp_time = None
        if isinstance(exp_time, datetime):
            db_exp_time = exp_time.astimezone(UTC).replace(tzinfo=None) if exp_time.tzinfo else exp_time
        elif isinstance(exp_time, int):
            db_exp_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=exp_time)
        url = urldata(
            short_url=custom_alias,
            long_url=long_url,
            created_at=datetime.now(UTC).replace(tzinfo=None),
            click_count=0,
            user_id=user_id,
            exp_time=db_exp_time,
            webhook_url=webhook_url,
            ios_url=ios_url,
            android_url=android_url,
            password_hash=password_hash,
            fallback_url=fallback_url
        )
        
        # Calculate correct Redis cache TTL
        redis_ttl = 3600
        is_expired = False
        if db_exp_time:
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            seconds_left = int((db_exp_time - now_naive).total_seconds())
            if seconds_left <= 0:
                is_expired = True
            else:
                redis_ttl = min(3600, seconds_left)

        is_dynamic = bool(webhook_url or ios_url or android_url or password_hash or fallback_url)

        try:
            if is_expired:
                redis_client.set(custom_alias, "Expired", ex=3600)
            elif is_dynamic:
                redis_client.set(custom_alias, "DYNAMIC", ex=3600)
            else:
                redis_client.set(custom_alias, long_url, ex=redis_ttl)
        except Exception as re:
            logger.warning(f"Redis is Offline falling back to Database: {re}")
        add_to_db(url)
        return custom_alias


def ban_in_cache(short_url: str):
    redis_client.set(short_url, "BANNED", ex=3600)

def serve_url(short_url : str):
    cached = None
    try:
        cached = redis_client.get(short_url)
    except Exception as re:
        logger.warning(f"Redis Offline, falling back to database: {re}")
    if cached:
        return cached

    from sqlmodel import Session, select
    from database import engine
    from models import urldata
    
    with Session(engine) as session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url = session.exec(statement).first()
        if url is None:
            logger.info(f"URL resolution requested but code does not exist: {short_url}")
            return None
            
        # Check expiration
        is_expired = False
        if url.exp_time:
            exp_utc = url.exp_time.astimezone(UTC).replace(tzinfo=None) if url.exp_time.tzinfo else url.exp_time
            now_utc = datetime.now(UTC).replace(tzinfo=None)
            if exp_utc < now_utc:
                is_expired = True
                
        if is_expired:
            try:
                redis_client.set(short_url, "Expired", ex=3600)
            except Exception as re:
                logger.warning(f"Redis Offline: {re}")
            return "Expired"
            
        if url.is_banned:
            try:
                redis_client.set(short_url, "BANNED", ex=3600)
            except Exception as re:
                logger.warning(f"Redis Offline: {re}")
            return "BANNED"
            
        # Check if the URL has premium dynamic properties
        is_dynamic = bool(url.webhook_url or url.ios_url or url.android_url or url.password_hash or url.fallback_url)
        if is_dynamic:
            try:
                redis_client.set(short_url, "DYNAMIC", ex=3600)
            except Exception as re:
                logger.warning(f"Redis Offline: {re}")
            return "DYNAMIC"

        # Calculate correct Redis cache TTL
        redis_ttl = 3600
        if url.exp_time:
            exp_utc = url.exp_time.astimezone(UTC).replace(tzinfo=None) if url.exp_time.tzinfo else url.exp_time
            now_utc = datetime.now(UTC).replace(tzinfo=None)
            seconds_left = int((exp_utc - now_utc).total_seconds())
            if seconds_left > 0:
                redis_ttl = min(3600, seconds_left)
                
        # Cache the valid long URL
        try:
            redis_client.set(short_url, url.long_url, ex=redis_ttl)
        except Exception as re:
            logger.warning(f"Redis Offline: {re}")
            
        return url.long_url

