import readline
import configparser
from datetime import datetime
from random import uniform



def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


@singleton
class Config:

    def __init__(self):
        self.PATH_TO_DICT = 'src/config.ini'
        self.parser = configparser.RawConfigParser(inline_comment_prefixes=None)
        self.__refresh()
    
    def __getitem__(self, key):
        return self.config[key]

    def __refresh(self):
        self.parser.read(self.PATH_TO_DICT)
        self.config = dict(self.parser.items('PARAMETERS'))

    def save(self):
        for k, v in self.config.items():
           self.parser.set('PARAMETERS', k, v)
        with open(self.PATH_TO_DICT, 'w') as configfile:
            self.parser.write(configfile)

    def update(self, modified_dict:dict):
        self.config.update(modified_dict)


config = Config()


true_values = {'true','yes','1','on'}
def boolinize(s:str):
    return s in true_values


def save_log(traceback):
    with open('log.txt', 'a') as file:
        file.write('\n@' + str(datetime.now()) + ' | ' + str(traceback))

def print_log(traceback):
    print(f"{str(datetime.now())} | {traceback}")

register_log = print_log if boolinize(config['debug'].lower()) else save_log


def safe_division(x, y, default=0):
    try:
        return x / y
    except ZeroDivisionError:
        return default


MIN_INTERVAL = float(config['min_query_interval'])
async def get_randomization(interval, randomize:int, eta:datetime) -> float:
    '''returns the randomization factor (in minutes)'''
    if eta is not None:
        abs_timedelta = abs((eta - datetime.now()).total_seconds())/60
        eta_adj = 0.00069*(abs_timedelta)**1.618
    else:
        eta_adj = 0
    noise = uniform(-randomize*interval, randomize*interval)*0.01
    time_wait = eta_adj + noise
    return max(round(time_wait,2), MIN_INTERVAL)


def rlinput(prompt, prefill=''):
   readline.set_startup_hook(lambda: readline.insert_text(str(prefill)))
   try:
      return input(prompt)
   finally:
      readline.set_startup_hook()

    
