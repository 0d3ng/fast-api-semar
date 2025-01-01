#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-01 16:14:00
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-01 16:13:59
#  File: test_sensor_routes.py
#  Description:
#  """
import datetime
import unittest
import random

import pytz
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


class MyTestCase(unittest.TestCase):

    # Fungsi untuk generate nilai acak dalam rentang tertentu

    @staticmethod
    def generate_random(min_val, max_val, decimals=2):
        return round(random.uniform(min_val, max_val), decimals)

    # Fungsi untuk membuat payload JSON secara dinamis

    def generate_sensor_data(self):
        return {
            "timestamp": datetime.datetime.now(tz=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp sekarang
            "data": {
                "temperature": self.generate_random(20, 30),  # Suhu (20°C - 30°C)
                "humidity": self.generate_random(30, 60),  # Kelembapan (%)
                "pressure": self.generate_random(950, 1050),  # Tekanan (hPa)
                "gas_resistance": self.generate_random(10000, 50000),  # Gas Resistance (Ohm)
                "co2": self.generate_random(400, 2000),  # CO2 (ppm)
                "voc": self.generate_random(0.5, 10),  # VOC (ppm)
                "iaq_index": self.generate_random(0, 500),  # IAQ Index (0-500)
                "iaq_accuracy": random.randint(0, 3)  # IAQ Accuracy (0-3)
            }
        }

    def test_insert(self):
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c3JfaWQiOiI2NzZjOTJkOGRkODhmNzk0ZmViZmE0ZDMiLCJ1c2VybmFtZSI6ImFkbWluIiwiZGV2X2lkIjoiNjc3NGQxMDkxMWVjY2ExYmU4MzU0NGQyIiwiZGV2X2NvZGUiOiJzYmJ1NXciLCJleHAiOjE3MzczOTE3NTl9.VwYdlRzZ2Y4g5vSD5En9zeEn9CppQRlJAOHfnMyJCHo"
        data = self.generate_sensor_data()
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(f"/api/v1/sensors", json=data, headers=headers)
        print(f"response: {response.text} code: {response.status_code}")
        assert response.status_code == 200


if __name__ == '__main__':
    unittest.main()
