from sonyflake import SonyFlake
from datetime import datetime , UTC
from base62 import encode_base62
from models import urldata
from database import add_to_db, get_long_url, is_long_url_exists
import redis
import time

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


def add_url():
    
    long_url = input("Enter the long url: ")
    short_url = get_short_url()
    url = urldata(
        short_url=short_url,
        long_url=long_url,
        created_at= datetime.now(UTC),
        click_count=0
    )
    exists = is_long_url_exists(long_url)
    if exists:
        pass
    else: 
        redis_client.set(
            short_url,
            long_url,
            ex=3600
            )
        add_to_db(url)


def serve_url(short_url : str):
    start_time = time.perf_counter()
    cached = redis_client.get(short_url)
    end_time = time.perf_counter()

    if cached:
        pass
        print(cached)
        print(f"redis time : {(end_time-start_time)*1000}")
    else:   
        start_time = time.perf_counter()
        long_url = get_long_url(short_url)
        end_time = time.perf_counter()
        if long_url:
            redis_client.set(
                short_url,
                long_url,
                ex = 3600
            )
            print(f"DB time : {(end_time-start_time)*1000}")
            print(long_url)
            
        else:
            print("URL does not exists")

def main():
    print(" 1. for Adding url 2. for fetching url")
    entry = int(input("Enter choice: "))
    if entry == 1:
        add_url()

    elif entry == 2:
        short_url = input("Enter short url: ")
        serve_url(short_url)

if __name__ == "__main__":
    main()
