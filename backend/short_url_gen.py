from sonyflake import SonyFlake
from datetime import datetime , UTC
from base62 import encode_base62
from models import urldata
from database import add_to_db, get_long_url, is_long_url_exists, mark_url_banned
import redis
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

def add_url(long_url : str, user_id: Optional[int] = None):
    
    exists = is_long_url_exists(long_url, user_id=user_id)
    if exists:
        return exists
    short_url = get_short_url()
    url = urldata(
        short_url=short_url,
        long_url=long_url,
        created_at= datetime.now(UTC),
        click_count=0,
        user_id=user_id
    )
    try:
        redis_client.set(
            short_url,
            long_url,
            ex=3600
            )
    except:
        print("Warning: Redis is Offline falling back to DataBase.")
    add_to_db(url)
    return short_url

def ban_in_cache(short_url: str):
    redis_client.set(short_url, "BANNED", ex=3600)

def serve_url(short_url : str):
    cached = None
    try:
        cached = redis_client.get(short_url)
    except:
        print("Warning: Reddis Offline, Fallback to DataBase.")
    if cached:
        return cached
    else:   
        long_url = get_long_url(short_url)
        if long_url:
            if cached:
                redis_client.set(
                    short_url,
                    long_url,
                    ex = 3600
                )
            else:
                print("Warning: Redis Offline, No cache storage available.")
            return long_url
            
        else:
            print("URL does not exist")

