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


def get_randomization(interval, randomize:int, eta:datetime) -> float:
    '''returns the randomization factor (in minutes)'''
    MIN_INTERVAL = float(config['min_query_interval'])
    if isinstance(eta, datetime):
        abs_timedelta = abs((eta - datetime.now()).total_seconds())/60
        eta_adj = 0.00069*(abs_timedelta)**1.618
    else:
        eta_adj = 0
    noise = uniform(-randomize*interval, randomize*interval)*0.01
    time_wait = eta_adj + noise
    return round(time_wait,2) if interval+time_wait > MIN_INTERVAL else MIN_INTERVAL


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
