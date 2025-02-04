#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-02-04 14:27:11
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-02-04 14:27:11
#   File: amedas_scheduler.py
#   Description:
#   """
from app.services.amedas_service import AmedasService
from app.utils.amedas import get_all_observation_data
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def start_amedas_scheduler():
    try:
        amedas = None
        try:
            amedas = await AmedasService.get_sensor_data_latest()
        except Exception as e:
            logger.error(e)
            datas = await get_all_observation_data(is10minutes=True)

    except Exception as a:
        logger.error(a)
