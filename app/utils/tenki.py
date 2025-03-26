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

url = "https://tenki.jp/pollen/7/36/6610/33100/"

translator = Translator()


async def translate_text(text):
    translated = await translator.translate(text, src='ja', dest='en')
    return translated.text


async def get_current_pollen():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.ChromiumDriver(service=Service(ChromeDriverManager().install()), options=chrome_options)
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
        print(f"Pollen: {pollen_trans}")
        print(f"Weather: {weather_trans}")
        print(f"High Temp: {high_temp}")
        print(f"Low Temp: {low_temp}")
        print(f"Precipitation: {precip}")
        return {
            "pollen": pollen_trans,
            "weather": weather_trans,
            "high_temp": high_temp,
            "low_temp": low_temp,
            "precip": precip
        }
    except TimeoutException as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(get_current_pollen())
