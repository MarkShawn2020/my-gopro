import subprocess
import time

from base.config import CONFIG_WIFI_GOPRO
from base.log import logger


def connect_wifi(name, pswd):
    """
    ref: - [Switch Wi-Fi networks from macOS Terminal / Michael Lee](https://michaelsoolee.com/switch-wifi-macos-terminal/#:~:text=macOS%20provides%20a%20command%20line,use%20the%20option%2C%20%2Dsetairportnetwork%20.)
    :param name:
    :param pswd:
    :return:
    """
    time.sleep(3)
    logger.info(f"connecting to wifi: {name}")
    # 必须加上`/usr/sbin/`前缀，否则无法在`cron`中运行，因为它默认只有`/usr/bin:/bin`的PATH
    command = f"/usr/sbin/networksetup -setairportnetwork en0 \"{name}\" \"{pswd}\""
    result = subprocess.getoutput(command)
    # 返回为空表示连接上
    assert result == "", f"command: {command}, result: {result}"
    logger.info('√')
    # 等待一点时间，等网络稳定
    time.sleep(3)


def is_wifi_connected():
    return subprocess.getoutput("/Sy*/L*/Priv*/Apple8*/V*/C*/R*/airport -I | awk '/ SSID:/ {print $2}'") == \
           CONFIG_WIFI_GOPRO[0]
