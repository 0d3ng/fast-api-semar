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
            full_key = f"{parent_key}.{key}" if parent_key else key
            values.extend(extract_values(value, full_key))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            full_key = f"{parent_key}[{index}]"
            values.extend(extract_values(value, full_key))
    else:
        values.append((parent_key, data))

    return values


# Contoh data JSON
data = {
    "dht": {
        "viciTemperature": 21,
        "viciHumidity": 38,
        "viciLuminosity": 58
    },
    "npk1": {
        "soilHumidity": 40,
        "soilTemperature": 25,
        "soilConductivity": 41,
        "soilPh": 8,
        "soilNitrogen": 18,
        "soilPhosphorus": 48,
        "soilPotassium": 24
    },
    "npk2": {
        "soilHumidity": 10,
        "soilTemperature": 32,
        "soilConductivity": 44,
        "soilPh": 8,
        "soilNitrogen": 34,
        "soilPhosphorus": 27,
        "soilPotassium": 14
    }
}

# Ekstrak semua nilai
result = extract_values(data)

# Cetak hasil
for key, value in result:
    print(f"{key}: {value}")
