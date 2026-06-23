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

def add_url(long_url : str, user_id: Optional[int] = None, exp_time : Optional[int | datetime] = None):
    
    exists = is_long_url_exists(long_url, user_id=user_id)
    if exists:
        return exists
    db_exp_time = None
    if isinstance(exp_time, datetime):
        db_exp_time = exp_time
    elif isinstance(exp_time, int):
        db_exp_time = datetime.now(UTC) + timedelta(hours=exp_time)
    short_url = get_short_url()
    url = urldata(
        short_url=short_url,
        long_url=long_url,
        created_at= datetime.now(UTC),
        click_count=0,
        user_id=user_id,
        exp_time=db_exp_time
    )
    try:
        redis_client.set(
            short_url,
            long_url,
            ex=3600
            )
    except Exception as re:
        logger.warning(f"Redis is Offline falling back to Database: {re}")
    add_to_db(url)
    return short_url


def add_custom_url(long_url, custom_alias, user_id: Optional[int] = None, exp_time : Optional[int | datetime] = None):
    exists = is_long_url_exists(long_url)
    if exists:
        return exists
    does_exists = is_alias_exists(custom_alias)
    if does_exists:
        return None
    else:
        db_exp_time = None
        if isinstance(exp_time, datetime):
            db_exp_time = exp_time
        elif isinstance(exp_time, int):
            db_exp_time = datetime.now(UTC) + timedelta(hours=exp_time)
        url = urldata(
            short_url=custom_alias,
            long_url=long_url,
            created_at=datetime.now(UTC),
            click_count=0,
            user_id=user_id,
            exp_time=db_exp_time
        )
        try:
            redis_client.set(
                custom_alias,
                long_url,
                ex=3600
                )
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
    else:   
        long_url = get_long_url(short_url)
        if long_url:
            try:
                redis_client.set(
                    short_url,
                    long_url,
                    ex=3600
                )
            except Exception as re:
                logger.warning(f"Redis Offline, no cache storage available: {re}")
            return long_url
            
        else:
            logger.info(f"URL resolution requested but code does not exist: {short_url}")

