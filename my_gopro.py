import asyncio
import logging
import os
import time
from binascii import hexlify
from datetime import datetime
from typing import List

import requests
from bleak import BleakScanner, BleakClient

from base.const import COMMAND_REQ_UUID, GOPRO_WIFI_BASE_URL, GOPRO_WIFI_GP_COMMAND, GOPRO_MEDIA_DIR
from base.config import CONFIG_WIFI_GOPRO, CONFIG_WIFI_HOME, CURRENT_DATA_PATH
from base.log import logger
from base.utils import get_media_online_path
from base.wifi import connect_wifi, is_wifi_connected

# suppress unnecessary mac ble error
logging.getLogger("bleak.backends.corebluetooth.scanner").setLevel(logging.CRITICAL)


class MyGoPro:

    def __init__(self):
        self._client = None
        self._event = asyncio.Event()
        self._current_data_path = CURRENT_DATA_PATH

    async def connect_ble(self):

        def notification_handler(handle: int, data: bytes) -> None:
            logger.info(f'<--- Response: {handle=}: {hexlify(data, ":")!r}')
            # Notify the writer
            self._event.set()

        logger.info(f"\n==== datetime: {datetime.now()}")
        logger.warning("电脑第一次与gopro配对时，需要保持gopro处于设置面板选中quik应用连接界面，直到收到所有返回消息方可确认配对成功")
        logger.warning("程序运行之时，请确保没有其他进程正在执行，手机quik不要处于预览状态，否则将导致连接不上！")
        try:
            gopro_device = None
            count = 0
            # 1. 扫描蓝牙设备。正常情况下，要扫描1-2遍。
            while not gopro_device:
                logger.info(f"---- Scanning for bluetooth devices... [#{count}]")
                # 需要蓝牙权限，例如pycharm、terminal、iterm之类的应用
                for device in await BleakScanner.discover(timeout=5):
                    logger.info(f"detected ble device: {device.name}")
                    if device.name.startswith("GoPro"):
                        gopro_device = device
                count += 1
            logger.info(f"found gopro：{gopro_device.name}")

            # 2. 连接蓝牙设备。配对自动进行，mac平台跳过（待确认）。
            logger.info(f"----- Establishing BLE connection to {gopro_device.name}...")
            client = BleakClient(gopro_device)
            await client.connect(timeout=30)  # 太短的话会导致连接失败
            logger.info("BLE Connected!")

            # 3. 获取通知。
            logger.info("---- Enabling notifications...")
            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties:
                        logger.info(f"Enabling notification on char {char.uuid}")
                        await client.start_notify(char, notification_handler)
            logger.info("Done enabling notifications")

            self._client = client
        except Exception as e:
            logger.error(f"Connection establishment failed: {e}")
            raise e

    async def _send_command(self, data: List[int], desc: str = None):
        if not self._client:
            await self.connect_ble()
        if desc is None:
            desc = f"Sending command of: {data}"
        desc = "---> Requesting: " + desc
        logger.info(desc)

        self._event.clear()
        await self._client.write_gatt_char(COMMAND_REQ_UUID, bytearray(data), True)
        await self._event.wait()  # Wait to receive the notification response
        time.sleep(2)  # 比如开启wifi之间就需要时间间隔

    async def send_command_load_timelapse_preset(self):
        # ref: https://gopro.github.io/OpenGoPro/ble_2_0#commands-quick-reference
        await self._send_command([0x04, 0x3E, 0x02, 0x03, 0xEA], "Loading timelapse preset")

    async def send_command_enable_shutter(self, on: bool):
        await self._send_command([3, 1, 1, on], "Control shutter: " + ("ON" if on else "OFF"))

    async def send_command_enable_wifi(self, on: bool):
        """
        wifi名称和密码的程序化获取方式，参见`tutorial_5_connect_wifi/wifi_enable.py`
        :param on:
        :return:
        """
        await self._send_command([0x03, 0x17, 0x01, on], "Control wifi: " + ("ON" if on else "OFF"))

    def _check_wifi(func):
        """
        对需要使用wifi的函数装饰检查与修复
        :return:
        """

        def wrapper(self, *args, **kwargs):
            if not is_wifi_connected():
                self.send_command_enable_wifi(True)
            return func(self, *args, **kwargs)

        return wrapper

    @_check_wifi
    def list_all_media(self):
        url = GOPRO_WIFI_BASE_URL + "/gopro/media/list"
        result = requests.get(url).json()
        logger.debug(result)
        return result

    @_check_wifi
    def download_single_media(self, fn: str):
        logger.info(f"downloading file: {fn}")
        result = requests.get(get_media_online_path(fn)).content
        fp = os.path.join(self._current_data_path, fn)
        with open(fp, "wb") as f:
            logger.info(f"saving into: {fp}")
            f.write(result)
            logger.info("√")

    def _delete_media(self, option):
        url = GOPRO_WIFI_GP_COMMAND + "/storage/delete" + option
        res = requests.get(url).json()
        logger.info(res if res else '√')

    @_check_wifi
    def delete_single_media(self, media_name: str):
        """
        删除单个文件时，网址结尾的"delete"不能带"/"
        :param media_name:
        :return:
        """
        logger.warning(f"deleting media: {media_name}")
        self._delete_media(option=f"?p={GOPRO_MEDIA_DIR}/{media_name}")

    @_check_wifi
    def delete_all_media(self):
        logger.warning("deleting all the media")
        self._delete_media("/all")


async def task_daily_download_all_the_videos():
    my_gopro = MyGoPro()

    # connect_ble part
    await my_gopro.connect_ble()

    # wifi part
    await my_gopro.send_command_enable_shutter(False)  # wifi打开之间需要停止拍摄
    await my_gopro.send_command_enable_wifi(True)
    connect_wifi(*CONFIG_WIFI_GOPRO)
    logger.info("---- downloading all the media")
    for dir in my_gopro.list_all_media()["media"]:
        logger.info(f"traverse media in dir: {dir['d']}")
        for file in dir["fs"]:
            fn = file["n"]
            my_gopro.download_single_media(fn)
            my_gopro.delete_single_media(fn)
    # TODO：将gopro无线桥接到路由器，从而化简该步
    # 最终要保证wifi回来
    connect_wifi(*CONFIG_WIFI_HOME)
    await my_gopro.send_command_enable_wifi(False)

    # continue part
    await my_gopro.send_command_load_timelapse_preset()
    await my_gopro.send_command_enable_shutter(True)


if __name__ == '__main__':
    # 若以下任务是类的一个方法，则需要使用loop，如果是一个全局函数，则可以直接用run，参考：https://cloud.tencent.com/developer/article/1598240
    asyncio.run(task_daily_download_all_the_videos())
