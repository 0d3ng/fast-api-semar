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
from app.utils.config import DELAY_TENKI
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
        await asyncio.sleep(60 * DELAY_TENKI)  # 60 minutes


async def start_tenki_service():
    global running
    local_tz = tzlocal.get_localzone()
    local_date = datetime.now(tz=pytz.UTC).date()
    try:
        tenki = await TenkiServices.get_last_tenki()
        if tenki:
            logger.info(f"db: {tenki}")
            try:
                tenki_scrap = await get_current_pollen()
                if tenki_scrap:
                    logger.info(f"pollen: {tenki_scrap}")
                    # logger.info(f"{tenki.date_pollen.astimezone(local_tz).date()} {local_date}")
                    if tenki.date_pollen.astimezone(local_tz).date() == local_date:
                        logger.info("Date same")
                        # logger.info(f"{tenki.temperature_high} {tenki_scrap["high_temp"]}")
                        clean_high_temp = tenki_scrap["high_temp"].strip()
                        clean_low_temp = tenki_scrap["low_temp"].strip()
                        if tenki.weather == tenki_scrap["weather"] and tenki.pollen == tenki_scrap["pollen"] and int(
                                tenki.precipitation) == int(tenki_scrap["precip"]) and tenki.temperature_low == int(
                            clean_low_temp) and int(tenki.temperature_high) == int(clean_high_temp):
                            logger.info("Data similar")
                        else:
                            logger.info("to be insert")
                            tenki_new: TenkiCreate = TenkiCreate(
                                date_pollen=local_date,
                                pollen=tenki_scrap["pollen"],
                                precipitation=tenki_scrap["precip"],
                                temperature_high=tenki_scrap["high_temp"],
                                temperature_low=tenki_scrap["low_temp"],
                                weather=tenki_scrap["weather"]
                            )
                            if await TenkiServices.insert(tenki_new):
                                logger.info(f"data added {tenki_new}")
                    else:
                        logger.info("Date different")
                        tenki_new: TenkiCreate = TenkiCreate(
                            date_pollen=local_date,
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
        try:
            tenki_scrap = await get_current_pollen()
            if tenki_scrap:
                logger.info(f"pollen: {tenki_scrap}")
                tenki_new: TenkiCreate = TenkiCreate(
                    date_pollen=local_date,
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


if __name__ == "__main__":
    asyncio.run(service_tenki_scheduler())
