#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-04-25 15:31:39
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-04-25 15:31:39
#   File: webdrivermanager.py
#   Description:
#   """

import asyncio
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

shared_driver = None
driver_lock = asyncio.Lock()

async def get_shared_driver():
    global shared_driver
    async with driver_lock:
        if shared_driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--remote-debugging-port=0")
            chrome_options.add_argument("--disable-cache")
            chrome_options.add_argument("--disk-cache-dir=/dev/null")

            shared_driver = webdriver.ChromiumDriver(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return shared_driver

async def close_shared_driver():
    global shared_driver
    async with driver_lock:
        if shared_driver:
            shared_driver.quit()
            shared_driver = None
