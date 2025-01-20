#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-20 00:13:10
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-20 00:13:10
#  File: test_amedas_services.py
#  Description:
#  """

import unittest

from app.services.amedas_service import AmedasService
from app.utils.amedas import get_all_observation_data


class MyTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_insert(self):
        amedas = get_all_observation_data(True)
        await AmedasService.insert(amedas)


if __name__ == '__main__':
    unittest.main()
