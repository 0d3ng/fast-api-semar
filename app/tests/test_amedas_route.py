#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-20 17:32:20
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-20 17:32:20
#   File: test_amedas_route.py
#   Description:
#   """

import unittest

from starlette.testclient import TestClient

from app.main import app
from app.utils.amedas import get_all_observation_data

client = TestClient(app)


class AmedasTestCase(unittest.TestCase):
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c3JfaWQiOiI2NzZjOTJkOGRkODhmNzk0ZmViZmE0ZDMiLCJ1c2VybmFtZSI6ImFkbWluIiwiZGV2X2lkIjoiNjc3NGQxMDkxMWVjY2ExYmU4MzU0NGQyIiwiZGV2X2NvZGUiOiJzYmJ1NXciLCJleHAiOjE3MzczOTE3NTl9.VwYdlRzZ2Y4g5vSD5En9zeEn9CppQRlJAOHfnMyJCHo"
    headers = {"Authorization": f"Bearer {token}"}

    def test_get_last(self):
        response = client.get(f"/api/v1/amedas", headers=self.headers)
        print(f"response: {response.text} code: {response.status_code}")

    def test_bulk_insert(self):
        data = get_all_observation_data(is10minutes=True)
        response = client.post(f"/api/v1/amedas", headers=self.headers)
        print(f"response: {response.text} code: {response.status_code}")


if __name__ == '__main__':
    unittest.main()
