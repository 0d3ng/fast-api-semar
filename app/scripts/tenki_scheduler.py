#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-03-26 15:18:56
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-03-26 15:18:56
#   File: tenki_scheduler.py
#   Description:
#   """
import asyncio
from datetime import datetime

import pytz
import tzlocal

from app.schemas.tenki_schema import TenkiCreate
from app.services.tenki_services import TenkiServices
from app.utils.logger import get_logger
from app.utils.tenki import get_current_pollen

logger = get_logger(__name__)
running = True


async def service_tenki_scheduler():
    while running:
        logger.info("Starting tenki service")
        ascii_art = r"""
        ___________            __   .__ 
        \__    ___/___   ____ |  | _|__|
          |    |_/ __ \ /    \|  |/ /  |
          |    |\  ___/|   |  \    <|  |
          |____| \___  >___|  /__|_ \__|
                     \/     \/     \/   
        """
        logger.info(ascii_art)
        await start_tenki_service()
        await asyncio.sleep(60 * 1)  # 1 minutes


async def start_tenki_service():
    global running
    try:
        tenki = await TenkiServices.get_last_tenki()
        local_tz = tzlocal.get_localzone()
        packet_datetime = datetime.now(local_tz)
        packet_datetime = pytz.utc.localize(packet_datetime)
        local_datetime = packet_datetime.astimezone(local_tz)
        local_date = local_datetime.date()
        if tenki:
            logger.info(f"db: {tenki}")
            try:
                tenki_scrap = await get_current_pollen()
                if tenki_scrap:
                    logger.info(f"pollen: {tenki_scrap}")
                    if tenki.weather == tenki_scrap["weather"] and tenki.pollen == tenki_scrap[
                        "pollen"] and tenki.precipitation == tenki_scrap["precip"] and tenki.temperature_high == \
                            tenki_scrap["high_temp"] and tenki.temperature_low == tenki_scrap["low_temp"]:
                        logger.info("Data similar")
                    else:
                        tenki_new: TenkiCreate = TenkiCreate(
                            date=local_date,
                            pollen=tenki_scrap["pollen"],
                            precipitation=tenki_scrap["precip"],
                            temperature_high=tenki_scrap["high_temp"],
                            temperature_low=tenki_scrap["low_temp"],
                            weather=tenki_scrap["weather"]
                        )
                        if await TenkiServices.insert(tenki_new):
                            logger.info(f"data added {tenki_new}")
            except Exception as e:
                logger.error(e)
        else:
            try:
                tenki_scrap = await get_current_pollen()
                if tenki_scrap:
                    logger.info(f"pollen: {tenki_scrap}")
                    if tenki.weather == tenki_scrap["weather"] and tenki.pollen == tenki_scrap[
                        "pollen"] and tenki.precipitation == tenki_scrap["precip"] and tenki.temperature_high == \
                            tenki_scrap["high_temp"] and tenki.temperature_low == tenki_scrap["low_temp"]:
                        logger.info("Data similar")
                    else:
                        tenki_new: TenkiCreate = TenkiCreate(
                            date=local_date,
                            pollen=tenki_scrap["pollen"],
                            precipitation=tenki_scrap["precip"],
                            temperature_high=tenki_scrap["high_temp"],
                            temperature_low=tenki_scrap["low_temp"],
                            weather=tenki_scrap["weather"]
                        )
                        if await TenkiServices.insert(tenki_new):
                            logger.info(f"data added {tenki_new}")
            except Exception as e:
                logger.error(e)
    except Exception as e:
        logger.error(e)
        running = False
