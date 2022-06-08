import os
import asyncio

from my_gopro import task_daily_download_all_the_videos

os.system("echo DATE: $(date -Iseconds)")
os.system("echo PYTHON: $(which python)")
os.system("echo PATH: $PATH")
os.system("echo WIFI: $(which networksetup)")

if __name__ == '__main__':
    asyncio.run(task_daily_download_all_the_videos())
