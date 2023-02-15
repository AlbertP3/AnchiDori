import readline
from common.config import Config
import logging
from datetime import datetime
from common.utils import boolinize
from functools import partial
import sys

config = Config(path='src/cli/config.ini')


def rlinput(prompt, prefill=''):
   readline.set_startup_hook(lambda: readline.insert_text(str(prefill)))
   try:
      return input(prompt)
   finally:
      readline.set_startup_hook()

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
    fh = logging.FileHandler('logs/cli.log', mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)
    register_log = partial(__save_log, log)
    sys.stderr.write = log.critical
