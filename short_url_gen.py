from sonyflake import SonyFlake
from datetime import datetime , UTC
from base62 import encode_base62

custom_epoch = datetime(2014, 9, 1, 0, 0, 0, tzinfo=UTC)

generator =  SonyFlake(custom_epoch)



def get_short_url() -> str:
    unique_id = get_unique_id()
    short_url = encode_base62(unique_id)
    return short_url

def get_unique_id() -> str:
    return generator.next_id()


def main():
    long_url = input("Enter the long url: ")
    short_url = get_short_url()
    mapping  = {
        "short_url": short_url,
        "long_url":long_url
    }
    print(mapping)


if __name__ == "__main__":
    main()
