import os

from base.const import DATA_ROOT_PATH
from base.log import logger
from base.utils import get_cur_date_str

CONFIG_WIFI_HOME = ("CMCC-24qw-5G", "mark2019")
CONFIG_WIFI_GOPRO = ("my-gopro", "xFQ-7rS-fvh")


CONFIG_DATA_ROOT_PATH = "/Volumes/Disk1/videos/gopro日常/延时生活"
if not os.path.exists(CONFIG_DATA_ROOT_PATH):
    logger.warning(f"NOT EXIST: {CONFIG_DATA_ROOT_PATH}")
    CONFIG_DATA_ROOT_PATH = DATA_ROOT_PATH
CURRENT_DATA_PATH = os.path.join(CONFIG_DATA_ROOT_PATH, get_cur_date_str())
if not os.path.exists(CURRENT_DATA_PATH):
    os.mkdir(CURRENT_DATA_PATH)
logger.info(f"CURRENT_DATA_PATH: {CURRENT_DATA_PATH}")

