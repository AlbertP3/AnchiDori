from common.config import Config
from common.utils import boolinize
from datetime import datetime
from random import uniform
import logging
import sys
import uuid
from functools import partial


config = Config(path='src/server/config.ini')


def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


__log_date_fmt = config['log_date_fmt']
def __save_log(logger:logging.Logger, traceback, log_level='INFO'):
    traceback = f"{datetime.now().strftime(__log_date_fmt)} {log_level} {traceback}"
    match log_level:
        case 'DEBUG': logger.debug(traceback)
        case 'INFO': logger.info(traceback) 
        case 'WARNING': logger.warning(traceback) 
        case 'ERROR': logger.error(traceback)
        case 'CRITICAL': logger.critical(traceback)

def __print_log(traceback, log_level='INFO'):
    print(f"{datetime.now().strftime(__log_date_fmt)} {log_level} {traceback}")

# Set logging function
if not boolinize(config['dump_logs'].lower()):
    register_log = __print_log
else:
    log = logging.getLogger('logger')
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler('logs/server.log', mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)
    register_log = partial(__save_log, log)
    sys.stderr.write = log.critical


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
def safe_date_fmt(d:datetime):
    try:
        return d.strftime(DATE_FMT) if isinstance(d, datetime) else d
    except (ValueError, TypeError):
        return str(d)

def safe_strptime(d:str):
    try:
        return datetime.strptime(d, DATE_FMT) if isinstance(d, str) else d
    except (ValueError, TypeError):
        return str(d)

