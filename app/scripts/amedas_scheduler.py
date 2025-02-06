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
import asyncio
from datetime import datetime

import pytz
import tzlocal

from app.schemas.amedas_schema import AmedasCreate
from app.services.amedas_service import AmedasService
from app.utils.amedas import get_all_observation_data, get_last_observation_data
from app.utils.logger import get_logger

logger = get_logger(__name__)

running = True


async def service_amedas_scheduler():
    while running:
        logger.info("Starting amedas service and waiting next process...")
        ascii_art = r"""
             ______ .______           ___   ____    __    ____  __                  
            /      ||   _  \         /   \  \   \  /  \  /   / |  |                 
           |  ,----'|  |_)  |       /  ^  \  \   \/    \/   /  |  |                 
           |  |     |      /       /  /_\  \  \            /   |  |                 
 __  __  __|  `----.|  |\  \----. /  _____  \  \    /\    /    |  `----. __  __  __ 
(__)(__)(__)\______|| _| `._____|/__/     \__\  \__/  \__/     |_______|(__)(__)(__)
                """
        logger.info(ascii_art)
        await start_amedas_scheduler()
        await asyncio.sleep(60 * 10)  # 10 minutes


async def start_amedas_scheduler():
    global running
    try:
        amedas = await AmedasService.get_sensor_data_latest()
        if amedas:
            local_tz = tzlocal.get_localzone()
            tz_amedas = amedas.timestamp
            if tz_amedas.tzinfo is None:
                tz_amedas = tz_amedas.replace(tzinfo=pytz.UTC)
            tz_amedas_local = tz_amedas.astimezone(local_tz)
            try:
                amedas_jmas = await get_all_observation_data(is10minutes=True)
                for amedas_jma in amedas_jmas:
                    dt_amedas = datetime.strptime(amedas_jma["timestamp"], '%Y-%m-%d %H:%M:%S')
                    if dt_amedas.tzinfo is None:
                        tz_jma = dt_amedas.replace(tzinfo=local_tz)
                    else:
                        tz_jma = dt_amedas.astimezone(local_tz)
                    logger.info(f"database: {tz_amedas_local.isoformat()} jma: {tz_jma.isoformat()}")
                    if tz_jma > tz_amedas:
                        amedas_new: AmedasCreate = AmedasCreate(
                            timestamp=tz_jma,
                            temperature=amedas_jma["temperature"],
                            wind_direction=amedas_jma["wind_direction"],
                            wind_speed=amedas_jma["wind_speed"],
                            humidity=amedas_jma["humidity"],
                            pressure=amedas_jma["pressure"],
                            sea_level_pressure=amedas_jma["sea_level_pressure"],
                            horizontal_visibility=amedas_jma["horizontal_visibility"]
                        )
                        if await AmedasService.insert_one(amedas_new):
                            logger.info(f"amedas inserted into database: {amedas_new}")
                    else:
                        logger.info(
                            f"no insert dt_amedas:{tz_amedas_local.isoformat()} db: {tz_jma.isoformat()}")
            except Exception as e:
                logger.error(e)
    except Exception as e:
        logger.warning(f"empty data: {e}")
        try:
            datas = await get_all_observation_data(is10minutes=True)
            logger.info(f"datas: {len(datas)} type: {type(datas)}")
            if datas:
                try:
                    res = await AmedasService.insert(datas)
                    if res:
                        logger.info(f"amedas inserted into database: {len(res)}")
                    else:
                        logger.warning(f"insert amedas failed")
                except Exception as e:
                    logger.error(e)
            else:
                logger.warning(f"no insert datas")
        except Exception as e:
            logger.error(e)
            running = False
