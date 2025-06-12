#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-03-26 14:02:19
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-03-26 14:02:19
#   File: tenki.py
#   Description:
#   """
import asyncio
import time

from googletrans import Translator
from selenium.common import TimeoutException
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.utils.driver_manager import get_shared_driver
from app.utils.logger import get_logger

logger = get_logger(__name__)
url = "https://tenki.jp/pollen/7/36/6610/33100/"
# url = "https://tenki-jp.translate.goog/pollen/7/36/6610/33100/?_x_tr_sl=id&_x_tr_tl=en&_x_tr_hl=en&_x_tr_pto=wapp"

translator = Translator()


async def translate_text(text):
    translated = await translator.translate(text, src='ja', dest='en')
    return translated.text


async def get_current_pollen():
    driver = await get_shared_driver()
    driver.get(url)
    driver.implicitly_wait(10)

    try:
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located((By.CLASS_NAME, "pollen-telop")))
        time.sleep(3)

        # Ambil informasi yang dibutuhkan
        pollen_count = driver.find_element(By.CLASS_NAME, "pollen-telop").text  # "Very common"
        weather = driver.find_element(By.CLASS_NAME, "weather-telop").text  # "Sunny"
        high_temp = driver.find_element(By.CLASS_NAME, "high-temp").text  # "25℃"
        low_temp = driver.find_element(By.CLASS_NAME, "low-temp").text  # "13℃"
        precip = driver.find_element(By.CLASS_NAME, "precip").text  # "0%"

        # Cetak hasil
        pollen_trans = await translate_text(pollen_count)
        weather_trans = await translate_text(weather)
        # print(f"Pollen: {pollen_count} {pollen_trans}")
        # print(f"Weather: {weather} {weather_trans}")
        # print(f"High Temp: {high_temp} {high_temp.replace("\u2103", "")}")
        # print(f"Low Temp: {low_temp} {low_temp.replace("\u2103", "")}")
        # print(f"Precipitation: {precip} {precip.replace("%", "")}")
        return {
            "pollen": pollen_trans,
            "weather": weather_trans,
            "high_temp": high_temp.replace("\u2103", ""),
            "low_temp": low_temp.replace("\u2103", ""),
            "precip": precip.replace("%", "")
        }
    except TimeoutException as e:
        logger.error(f"timeout: {e}")
        raise e
    except Exception as e:
        logger.error(f"exception: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(get_current_pollen())
