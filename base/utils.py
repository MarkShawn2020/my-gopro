import os
from datetime import date

from base.const import GOPRO_WIFI_BASE_URL, GOPRO_MEDIA_DIR


def get_media_online_path(media_name):
    return GOPRO_WIFI_BASE_URL + f"/videos/DCIM/{GOPRO_MEDIA_DIR}/{media_name}"


def get_cur_date_str():
    return date.today().isoformat()