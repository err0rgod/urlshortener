from sonyflake import SonyFlake
from datetime import datetime , UTC


custom_epoch = datetime.datetime(2014, 9, 1, 0, 0, 0, tzinfo=UTC)

generator =  SonyFlake(custom_epoch)



def get_short_url(long_url : str):
    unique_id = get_unique_id()
    short_url = base62_composition(unique_id)
    pass

def get_unique_id():
    return generator.next_id()

def base62_composition(unique_id : str):
    pass



