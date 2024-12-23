#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-23 16:09:12
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-23 16:09:12
#   File: test_device_services.py
#   Description:
#   """

import unittest

from app.services.device_service import DeviceService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeviceTestCase(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    async def test_get_active_all_devices():
        devices = await DeviceService.get_active_all_devices()
        for device in devices:
            print(f"device code: {device.code}")


if __name__ == '__main__':
    unittest.main()
