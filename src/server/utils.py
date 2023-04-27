import logging
from datetime import datetime
from random import uniform
import uuid
from time import process_time
from server import config

LOGGER = logging.getLogger('Utils')

def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


def get_randomization(interval, randomize:int) -> float:
    '''returns the randomization factor (in minutes)'''
    time_wait = uniform(-randomize*interval, randomize*interval)*0.01
    return round(time_wait,2)


def gen_token():
    return str(uuid.uuid4())


DATE_FMT = config['date_fmt']
def safe_date_fmt(d:datetime) -> str:
    try:
        return d.strftime(DATE_FMT) if isinstance(d, datetime) else str(d)
    except (ValueError, TypeError):
        return str(d)

def safe_strptime(d:str) -> datetime:
    try:
        return datetime.strptime(d, DATE_FMT) if isinstance(d, str) else d
    except (ValueError, TypeError):
        return str(d)

def timer(f):
    async def inner(*args, **kwargs):
        start = process_time()
        res = await f(*args, **kwargs)
        t = 1000*(process_time()-start)
        LOGGER.debug(f"{f.__qualname__} took {t:.5f}ms to finish", stacklevel=2)
        return res
    return inner

class warn_set(set):
    '''Set that precludes adding empty items'''
    def add(self, item):
        if not item: return
        super().add(item)