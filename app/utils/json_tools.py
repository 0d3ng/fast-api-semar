#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-30 11:19:50
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-30 11:19:50
#  File: json_tools.py
#  Description:
#  """

import json
import numbers


def extract_values(data, parent_key=''):
    """
    Ekstrak semua nilai dari JSON yang memiliki struktur dinamis.
    :param data: Data JSON (dict atau list)
    :param parent_key: Key dari elemen parent untuk pelacakan hierarki (opsional)
    :return: List of tuples (key path, value)
    """
    values = []

    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{parent_key}_{key}" if parent_key else key
            values.extend(extract_values(value, full_key))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            full_key = f"{parent_key}[{index}]"
            values.extend(extract_values(value, full_key))
    else:
        values.append((parent_key, data))
    return values


def extract_sensors(data, parent_key=''):
    values = extract_values(data, parent_key)
    data_dict = {key: value for key, value in values}
    # print(f"data dict: {data_dict} type: {type(data_dict)}")
    return data_dict
    # json_result = json.dumps(data_dict)
    # return json_result


def is_number(value):
    return isinstance(value, (int, float))

    # Contoh data JSON
    # data = {
    #     "dht": {
    #         "viciTemperature": 21,
    #         "viciHumidity": 38,
    #         "viciLuminosity": 58
    #     },
    #     "npk1": {
    #         "soilHumidity": 40,
    #         "soilTemperature": 25,
    #         "soilConductivity": 41,
    #         "soilPh": 8,
    #         "soilNitrogen": 18,
    #         "soilPhosphorus": 48,
    #         "soilPotassium": 24
    #     },
    #     "npk2": {
    #         "soilHumidity": 10,
    #         "soilTemperature": 32,
    #         "soilConductivity": 44,
    #         "soilPh": 8,
    #         "soilNitrogen": 34,
    #         "soilPhosphorus": 27,
    #         "soilPotassium": 14
    #     }
    # }

data = {
        "amedas": {
            "horizontal_visibility": 20,
            "humidity": 57,
            "pressure": 1024.1,
            "sea_level_pressure": 1025,
            "temperature": 3,
            "timestamp": "2025-02-10 22:10:00",
            "wind_direction": "WSW",
            "wind_speed": 4.8
        },
        "btevs1": {
            "co2": 903,
            "humidity": 25,
            "latitude": 0,
            "longitude": 0,
            "pm1": 1.3,
            "pm10": 1.4,
            "pm25": 1.4,
            "pm4": 1.4,
            "temp": 21.8,
            "timestamp": "2025-02-10 22:28:34"
        }
    }


# Ekstrak semua nilai
# print(data)
# result = extract_sensors(data)
# print(result)
