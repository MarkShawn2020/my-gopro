import os

from open_gopro.constants import GOPRO_BASE_UUID

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(BASE_PATH)
DATA_ROOT_PATH = os.path.join(PROJECT_PATH, "data")

COMMAND_REQ_UUID = GOPRO_BASE_UUID.format("0072")
COMMAND_RSP_UUID = GOPRO_BASE_UUID.format("0073")
WIFI_AP_SSID_UUID = GOPRO_BASE_UUID.format("0002")
WIFI_AP_PASSWORD_UUID = GOPRO_BASE_UUID.format("0003")

GOPRO_WIFI_BASE_URL = "http://10.5.5.9:8080"
GOPRO_WIFI_GP_COMMAND = GOPRO_WIFI_BASE_URL + "/gp/gpControl/command"
GOPRO_MEDIA_DIR = "100GOPRO"
