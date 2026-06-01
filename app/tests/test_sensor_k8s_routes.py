#   """
#   Copyright (c) 2026 lepen - All Rights Reserved
#   Created by lepen on 2026-06-01 11:12:05
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2026-06-01 11:12:05
#   File: test_sensor_k8s_routes.py
#   Description:
#   """
import datetime
import random
import unittest
from unittest.mock import patch, MagicMock

import pytz
import requests
from starlette.testclient import TestClient

from app.main import app
from app.middlewares.auth import verify_keycloak_token


class MyTestCase(unittest.TestCase):
    KEYCLOAK_URL = "https://keycloak.sinaungoding.com/realms/semar/protocol/openid-connect/token"
    TOKEN = None

    @classmethod
    def setUpClass(cls):
        """Jalankan sekali di awal untuk get token"""
        cls.client = TestClient(app)
        cls.get_token()

    @classmethod
    def get_token(cls):
        """Get token dari Keycloak"""
        payload = {
            "grant_type": "password",
            "client_id": "semar-app",
            "client_secret": "iuagRtS6ypqkDDicaQkdX3we9wXhloiR",
            "username": "testuser",
            "password": "123456"
        }
        try:
            response = requests.post(cls.KEYCLOAK_URL, data=payload)
            response.raise_for_status()
            data = response.json()
            cls.TOKEN = data.get("access_token")
            print(f"✅ Token berhasil didapat: {cls.TOKEN[:50]}...")
        except Exception as e:
            print(f"❌ Gagal get token: {e}")
            raise

    def generate_random(self, min_val, max_val, decimals=2):
        return round(random.uniform(min_val, max_val), decimals)

    def generate_sensor_data(self):
        return {
            "device_id": "6a1ce885b29436c8baf3ae91",
            "device_code": "s6zzdh",
            "timestamp": datetime.datetime.now(tz=pytz.UTC).isoformat(),
            "data": {
                "temperature": self.generate_random(20, 30),
                "humidity": self.generate_random(30, 60),
                "pressure": self.generate_random(950, 1050),
                "gas_resistance": self.generate_random(10000, 50000),
                "co2": self.generate_random(400, 2000),
                "voc": self.generate_random(0.5, 10),
                "iaq_index": self.generate_random(0, 500),
                "iaq_accuracy": random.randint(0, 3)
            }
        }

    def test_insert(self):
        """Test insert sensor data dengan mock auth"""
        try:
            sensor_data = self.generate_sensor_data()
            headers = {
                "Authorization": f"Bearer {self.TOKEN}",
                "Content-Type": "application/json"
            }

            response = self.client.post(
                "/api/v1/kub_sensors",
                json=sensor_data,
                headers=headers
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")

            self.assertEqual(response.status_code, 200)
        finally:
            # Clear override setelah test
            app.dependency_overrides.clear()


if __name__ == '__main__':
    unittest.main()