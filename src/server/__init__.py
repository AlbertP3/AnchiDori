import os
import sys
import logging
from common.config import Config

CWD = os.path.dirname(os.path.abspath(__file__))

# Setup configuration
config = Config(path=f'{CWD}/config.ini')

# Configure logging
logging.basicConfig(
    filename=os.path.realpath(f'{CWD}/../../logs/server.log'),
    filemode='a',
    format='%(asctime)s.%(msecs)05d [%(name)s] %(levelname)s %(message)s <%(filename)s(%(lineno)d)>',
    datefmt=config['log_date_fmt'],
    level=config.get('log_level', 'DEBUG')
    )
LOGGER = logging.getLogger('Server')
sys.stderr.write = LOGGER.critical
logging.getLogger('aiohttp.access').info = logging.debug
