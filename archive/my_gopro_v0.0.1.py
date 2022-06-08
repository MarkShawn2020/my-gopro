import asyncio
import logging
import os
import subprocess
import time
from typing import List

import requests
from bleak import BleakScanner, BleakClient
from open_gopro.constants import GOPRO_BASE_UUID

from config import WIFI_HOME, WIFI_GOPRO
from disk_move import exec_move

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UUIDs to write to and receive responses from, and read from
COMMAND_REQ_UUID = GOPRO_BASE_UUID.format("0072")
COMMAND_RSP_UUID = GOPRO_BASE_UUID.format("0073")
WIFI_AP_SSID_UUID = GOPRO_BASE_UUID.format("0002")
WIFI_AP_PASSWORD_UUID = GOPRO_BASE_UUID.format("0003")

GOPRO_BASE_URL = "http://10.5.5.9:8080"
GOPRO_GP_COMMAND = GOPRO_BASE_URL + "/gp/gpControl/command"
GOPRO_MEDIA_DIR = "100GOPRO"


async def connect_ble(notification_handler) -> BleakClient:
    logger.warning("程序运行之时，请确保没有其他进程正在执行，手机quik不要处于预览状态，否则将导致连接不上！")
    try:
        gopro_device = None

        # 1. 扫描蓝牙设备。正常情况下，要扫描1-2遍。
        while not gopro_device:
            logger.info("Scanning for bluetooth devices...")
            for device in await BleakScanner.discover(timeout=3):
                logger.info(f"detected ble device: {device.name}")
                if device.name.startswith("GoPro"):
                    gopro_device = device
        logger.info(f"found gopro：{gopro_device.name}")

        # 2. 连接蓝牙设备。配对自动进行，mac平台跳过（待确认）。
        logger.info(f"Establishing BLE connection to {gopro_device.name}...")
        client = BleakClient(gopro_device)
        await client.connect(timeout=30)  # 太短的话会导致连接失败
        logger.info("BLE Connected!")

        # 3. 获取通知。
        logger.info("Enabling notifications...")
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    logger.info(f"Enabling notification on char {char.uuid}")
                    await client.start_notify(char, notification_handler)
        logger.info("Done enabling notifications")

        return client
    except Exception as e:
        logger.error(f"Connection establishment failed: {e}")


async def send_command(data: List[int], desc: str = None):
    event = asyncio.Event()
    client = await connect_ble(lambda x, y: event.set())
    if desc is None:
        desc = f"Sending command of: {data}"
    logger.info(desc)

    event.clear()
    await client.write_gatt_char(COMMAND_REQ_UUID, bytearray(data), True)
    await event.wait()  # Wait to receive the notification response


async def load_timelapse_preset():
    # ref: https://gopro.github.io/OpenGoPro/ble_2_0#commands-quick-reference
    await send_command([0x04, 0x3E, 0x02, 0x03, 0xEA], "Loading timelapse preset")


async def control_shutter(on: bool):
    await send_command([3, 1, 1, on], "Control shutter: " + ("ON" if on else "OFF"))


async def control_wifi(on: bool):
    """
    wifi名称和密码的程序化获取方式，参见`tutorial_5_connect_wifi/wifi_enable.py`
    :param on:
    :return:
    """
    await send_command([0x03, 0x17, 0x01, on], "Control wifi: " + ("ON" if on else "OFF"))


def connect_wifi(name, pswd):
    """
    ref: - [Switch Wi-Fi networks from macOS Terminal / Michael Lee](https://michaelsoolee.com/switch-wifi-macos-terminal/#:~:text=macOS%20provides%20a%20command%20line,use%20the%20option%2C%20%2Dsetairportnetwork%20.)
    :param name:
    :param pswd:
    :return:
    """
    logger.info(f"connecting to wifi: {name}")
    result = subprocess.getoutput(f"networksetup -setairportnetwork en0 \"{name}\" \"{pswd}\"")
    # 返回为空表示连接上
    assert result == "", result
    logger.info("connected wifi")
    # 等待一点时间，等网络稳定
    time.sleep(3)


def get_media_list():
    url = GOPRO_BASE_URL + "/gopro/media/list"
    result = requests.get(url).json()
    print(result)
    return result


def get_media_online_path(media_name):
    return GOPRO_BASE_URL + f"/videos/DCIM/{GOPRO_MEDIA_DIR}/{media_name}"


def get_media_local_path(media_name):
    return os.path.abspath(media_name)


def download_media(fn: str):
    logger.info(f"downloading file: {fn}")
    result = requests.get(get_media_online_path(fn)).content
    fp = get_media_local_path(fn)
    with open(fp, "wb") as f:
        logger.info("saving into: ", fp)
        f.write(result)
        logger.info("saved")


def _delete_media(option):
    url = GOPRO_GP_COMMAND + "/storage/delete" + option
    res = requests.get(url)
    logger.info(f"deleted result: {res.json()}")


def delete_media(fn: str):
    logger.warning(f"deleting media: {fn}")
    _delete_media(option=f"?p={GOPRO_MEDIA_DIR}/{fn}")


def delete_all_media():
    logger.warning("deleting all the media")
    _delete_media("/all")


async def daily_download_all_the_videos():
    # connect_ble part
    await control_shutter(False)

    # wifi part
    await control_wifi(True)
    connect_wifi(*WIFI_GOPRO)
    for dir in get_media_list()["media"]:
        logger.info(f"traverse media in dir: {dir['n']}")
        for file in dir:
            fn = file["n"]
            # download_single_media(media_name)
            delete_media(fn)
    connect_wifi(*WIFI_HOME)
    await control_wifi(False)

    # continue part
    await load_timelapse_preset()
    await control_shutter(True)

    # disk part
    exec_move()


if __name__ == '__main__':
    asyncio.run(daily_download_all_the_videos())
