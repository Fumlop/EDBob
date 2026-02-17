import sys

import colorlog
import logging
from logging.handlers import RotatingFileHandler

_filename = 'autopilot.log'

# Define the logging config -- rotate at 1MB, keep 5 backups
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
                    datefmt='%H:%M:%S',
                    handlers=[RotatingFileHandler(_filename, maxBytes=1_000_000, backupCount=5, encoding='utf-8')])

logger = colorlog.getLogger('ed_log')

# Change this to debug if want to see debug lines in log file
logger.setLevel(logging.INFO)    # change to INFO for more... DEBUG for much more
logger.info(f'Python version: {sys.version}')

handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)  # change this to what is shown on console
handler.setFormatter(
    colorlog.ColoredFormatter('%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s',
        log_colors={
            'DEBUG':    'fg_bold_cyan',
            'INFO':     'fg_bold_green',
            'WARNING':  'bg_bold_yellow,fg_bold_blue',
            'ERROR':    'bg_bold_red,fg_bold_white',
            'CRITICAL': 'bg_bold_red,fg_bold_yellow',
	},secondary_log_colors={}

    ))
logger.addHandler(handler)
