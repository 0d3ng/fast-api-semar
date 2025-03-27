#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-03-26 14:59:19
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-03-26 14:59:19
#   File: tenki_services.py
#   Description:
#   """
import traceback
from datetime import datetime

import pytz
from fastapi import HTTPException

from app.models.tenki import Tenki
from app.schemas.tenki_schema import TenkiCreate, TenkiResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TenkiServices:
    @staticmethod
    async def insert(tenki: TenkiCreate):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            tenki_new: Tenki = Tenki(
                date_pollen=tenki.date_pollen,
                pollen=tenki.pollen,
                weather=tenki.weather,
                temperature_high=tenki.temperature_high,
                temperature_low=tenki.temperature_low,
                precipitation=tenki.precipitation,
                inserted_at=datetime_jpn
            )
            logger.info(f"Inserting {tenki_new} to database")
            result = await db.sensor_tenki.insert_one(tenki_new.model_dump(by_alias=True))
            if result.inserted_id:
                logger.info(f"Inserted {result.inserted_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to create tenki: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
        return False

    @staticmethod
    async def get_last_tenki():
        try:
            latest = await db.sensor_tenki.find_one(sort=[('inserted_at', -1)])
            if latest:
                logger.info(f"Last tenki found: {latest}")
                return TenkiResponse(**latest)
            raise HTTPException(status_code=404, detail="tenki not found")
        except Exception as e:
            logger.error(f"Failed to get tenki: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
