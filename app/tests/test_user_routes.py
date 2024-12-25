#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-25 20:59:11
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-25 20:59:11
#   File: test_user_routes.py
#   Description:
#   """
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login():
    form_data = {"username": "admin", "password": "admin"}
    response = client.post("/api/v1/login", data=form_data)
    print(response.json())
    print(response.json()["access_token"])
    assert response.status_code == 200
    return response.json()["access_token"]
