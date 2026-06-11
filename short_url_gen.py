from sonyflake import SonyFlake
from datetime import datetime , UTC
from base62 import encode_base62
from models import urldata
from database import add_to_db, get_long_url, is_long_url_exists, mark_url_banned
import redis
# from validations import check_safe_browsing

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)




custom_epoch = datetime(2014, 9, 1, 0, 0, 0, tzinfo=UTC)

generator =  SonyFlake(custom_epoch)



def get_short_url() -> str:
    unique_id = get_unique_id()
    short_url = encode_base62(unique_id)
    return short_url

def get_unique_id() -> str:
    return generator.next_id()


def add_url(long_url : str):
    
    exists = is_long_url_exists(long_url)
    if exists:
        return exists
    short_url = get_short_url()
    url = urldata(
        short_url=short_url,
        long_url=long_url,
        created_at= datetime.now(UTC),
        click_count=0
    )
    
    redis_client.set(
        short_url,
        long_url,
        ex=3600
        )
    add_to_db(url)
    return short_url

def ban_in_cache(short_url: str):
    redis_client.set(short_url, "BANNED", ex=3600)

def serve_url(short_url : str):
    
    # start_time = time.perf_counter()
    cached = redis_client.get(short_url)
    # end_time = time.perf_counter()

    if cached:
        return cached
        # print(f"redis time : {(end_time-start_time)*1000}")
    else:   
        # start_time = time.perf_counter()
        long_url = get_long_url(short_url)
        # end_time = time.perf_counter()
        if long_url:
            redis_client.set(
                short_url,
                long_url,
                ex = 3600
            )
            # print(f"DB time : {(end_time-start_time)*1000}")
            return long_url
            
        else:
            print("URL does not exist")

