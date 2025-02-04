#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-18 23:47:47
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-18 23:47:47
#  File: amedas.py
#  Description:
#  """
import asyncio
import re
import time
from datetime import datetime, timezone

from selenium.common import TimeoutException
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# 10 minutes
url = "https://www.jma.go.jp/bosai/amedas/#area_type=offices&area_code=330000&amdno=66408&format="


# 1 hour
# url = "https://www.jma.go.jp/bosai/amedas/#area_type=offices&area_code=330000&amdno=66408&format=table1h&lang=en&elems=43018"


async def get_all_observation_data(is10minutes: bool = False, wait: float = 5):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.ChromiumDriver(service=Service(ChromeDriverManager().install()), options=chrome_options)

    table_name = "table10min" if is10minutes else "table1h"
    # print(f"{url}{table_name}&lang=en&elems=4301e")
    driver.get(f"{url}{table_name}&lang=en&elems=4301e")
    driver.implicitly_wait(wait)
    # print(driver.page_source)
    try:
        WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.ID, "amd-table")))
        time.sleep(3)
        table_div = driver.find_element(By.ID, "amd-table")
        rows = table_div.find_elements(By.TAG_NAME, "tr")
        date_pattern = re.compile(r'\d{2}/\d{2}')
        date_str = None
        current_year = datetime.now(timezone.utc).year
        amedas_data = []
        for row in rows:
            if row.get_attribute('class') == "amd-table-tr-onthedot" or row.get_attribute(
                    'class') == "amd-table-tr-notonthedot":
                if row.text:
                    # print(f"{row.text}")
                    parts = row.text.split()
                    if date_pattern.match(parts[0]):
                        date_str = parts[0]
                        date_time = date_str + ' ' + parts[1]
                        temperature = parts[2]
                        wind_direction = parts[3]
                        wind_speed = parts[4]
                        humidity = parts[5]
                        pressure = parts[6]
                        sea_level_pressure = parts[7]
                        horizontal_visibility = parts[8]
                    else:
                        date_time = f"{date_str} {parts[0]}"
                        temperature = parts[1]
                        wind_direction = parts[2]
                        wind_speed = parts[3]
                        humidity = parts[4]
                        pressure = parts[5]
                        sea_level_pressure = parts[6]
                        horizontal_visibility = parts[7]
                    full_date_string = f'{current_year} {date_time}:00'
                    if "24:00" in full_date_string:
                        full_date_string = full_date_string.replace("24:00", "00:00")
                        date_time_obj = datetime.strptime(full_date_string, '%Y %m/%d %H:%M:%S')
                    else:
                        date_time_obj = datetime.strptime(full_date_string, '%Y %m/%d %H:%M:%S')
                    date_time_custom = date_time_obj.isoformat()
                    date_time_custom = date_time_custom.replace("T", " ")
                    data = {
                        "timestamp": date_time_custom,
                        "temperature": temperature,
                        "wind_direction": wind_direction,
                        "wind_speed": wind_speed,
                        "humidity": humidity,
                        "pressure": pressure,
                        "sea_level_pressure": sea_level_pressure,
                        "horizontal_visibility": horizontal_visibility
                    }
                    # print(data)
                    amedas_data.append(data)
        return amedas_data
    except TimeoutException:
        print("TimeoutException")
    # driver.quit()


async def get_last_observation_data(is10minutes: bool = False, wait: float = 5):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.ChromiumDriver(service=Service(ChromeDriverManager().install()), options=chrome_options)
    table_name = "table10min" if is10minutes else "table1h"
    # print(f"{url}{table_name}&lang=en&elems=4301e")
    driver.get(f"{url}{table_name}&lang=en&elems=4301e")
    driver.implicitly_wait(wait)
    # print(driver.page_source)
    try:
        WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.ID, "amd-table")))
        time.sleep(1)
        table_div = driver.find_element(By.ID, "amd-table")
        rows = table_div.find_elements(By.TAG_NAME, "tr")
        date_pattern = re.compile(r'\d{2}/\d{2}')
        date_str = None
        current_year = datetime.now(timezone.utc).year
        data = None
        for row in rows:
            if row.get_attribute('class') == "amd-table-tr-onthedot" or row.get_attribute(
                    'class') == "amd-table-tr-notonthedot":
                if row.text:
                    # print(f"{row.text}")
                    parts = row.text.split()
                    if date_pattern.match(parts[0]):
                        date_str = parts[0]
                        date_time = date_str + ' ' + parts[1]
                        temperature = parts[2]
                        wind_direction = parts[3]
                        wind_speed = parts[4]
                        humidity = parts[5]
                        pressure = parts[6]
                        sea_level_pressure = parts[7]
                        horizontal_visibility = parts[8]
                    else:
                        date_time = f"{date_str} {parts[0]}"
                        temperature = parts[1]
                        wind_direction = parts[2]
                        wind_speed = parts[3]
                        humidity = parts[4]
                        pressure = parts[5]
                        sea_level_pressure = parts[6]
                        horizontal_visibility = parts[7]
                    full_date_string = f'{current_year} {date_time}:00'
                    if "24:00" in full_date_string:
                        full_date_string = full_date_string.replace("24:00", "00:00")
                        date_time_obj = datetime.strptime(full_date_string, '%Y %m/%d %H:%M:%S')
                    else:
                        date_time_obj = datetime.strptime(full_date_string, '%Y %m/%d %H:%M:%S')
                    date_time_custom = date_time_obj.isoformat()
                    date_time_custom = date_time_custom.replace("T", " ")
                    data = {
                        "timestamp": date_time_custom,
                        "temperature": temperature,
                        "wind_direction": wind_direction,
                        "wind_speed": wind_speed,
                        "humidity": humidity,
                        "pressure": pressure,
                        "sea_level_pressure": sea_level_pressure,
                        "horizontal_visibility": horizontal_visibility
                    }
                    # print(data)
                    break
        # driver.quit()
        return data
    except TimeoutException as e:
        # driver.quit()
        raise Exception(e)


if __name__ == "__main__":
    # now = time.time()
    # # get_all_observation_data(is10minutes=True)
    # get_last_observation_data(is10minutes=True)
    # dif = time.time() - now
    # hours, rem = divmod(dif, 3600)
    # minutes, rem = divmod(rem, 60)
    # seconds, ms = divmod(rem, 1)
    # ms = int(ms * 1000)
    # print(f"Selisih waktu: {int(hours):02}:{int(minutes):02}:{int(seconds):02}.{ms:03}")
    async def main():
        now = time.time()
        # get_all_observation_data(is10minutes=True)
        data = await get_last_observation_data(is10minutes=True)
        dif = time.time() - now
        hours, rem = divmod(dif, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, ms = divmod(rem, 1)
        ms = int(ms * 1000)
        print(data)
        print(f"Selisih waktu: {int(hours):02}:{int(minutes):02}:{int(seconds):02}.{ms:03}")


    asyncio.run(main())
