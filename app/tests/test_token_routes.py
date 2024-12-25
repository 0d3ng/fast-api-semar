#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-25 20:45:08
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-25 20:45:08
#   File: test_token_routes.py
#   Description:
#   """
from starlette.testclient import TestClient

from app.main import app
from app.tests.test_user_routes import test_login

client = TestClient(app)

def test_get_token_by_device():
    token = test_login()
    headers = {"Authorization": f"Bearer {token}"}
    device_id = "676bea9eb3d4ef16816b2a89"
    response = client.get(f"/api/v1/tokens/device/{device_id}", headers=headers)
    print(response.text)
    assert response.status_code == 200
