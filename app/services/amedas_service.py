#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-19 23:54:26
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-19 23:54:26
#  File: amedas_service.py
#  Description:
#  """
import traceback
from datetime import datetime

import pytz
from dateutil.zoneinfo import tzfile
from fastapi import HTTPException

from app.models.amedas import Amedas
from app.schemas.amedas_schema import AmedasResponse, AmedasCreate
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AmedasService:
    @staticmethod
    async def insert(documents: list):
        try:
            amedas_list = []
            for document in documents:
                datetime_jpn = datetime.now(tz=pytz.UTC)
                timestamp = datetime.strptime(document['timestamp'], "%Y-%m-%d %H:%M:%S")
                timestamp = timestamp.astimezone(pytz.UTC)
                amedasnew: Amedas = Amedas(
                    timestamp=timestamp,
                    temperature=document['temperature'],
                    wind_speed=document['wind_speed'],
                    wind_direction=document['wind_direction'],
                    humidity=document['humidity'],
                    pressure=document['pressure'],
                    sea_level_pressure=document['sea_level_pressure'],
                    horizontal_visibility=document['horizontal_visibility'],
                    inserted_at=datetime_jpn
                )
                amedas_list.append(amedasnew.model_dump(by_alias=True))
            result = await db.sensor_amedas.insert_many(amedas_list)
            if result.inserted_ids:
                logger.info(f"Inserted {len(result.inserted_ids)} records")
                return {
                    "inserted: ": len(result.inserted_ids),
                    "ids": result.inserted_ids
                }
            raise HTTPException(status_code=500, detail="Create amedas fail")
        except Exception as e:
            logger.error(f"Failed to create sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def insert_one(amedas: AmedasCreate):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            logger.info(f"data prepare {amedas} to insert")
            timestamp = amedas.timestamp
            timestamp = timestamp.astimezone(pytz.UTC)
            amedasnew: Amedas = Amedas(
                timestamp=timestamp,
                temperature=amedas.temperature,
                wind_speed=amedas.wind_speed,
                wind_direction=amedas.wind_direction,
                humidity=amedas.humidity,
                pressure=amedas.pressure,
                sea_level_pressure=amedas.sea_level_pressure,
                horizontal_visibility=amedas.horizontal_visibility,
                inserted_at=datetime_jpn
            )
            result = await db.sensor_amedas.insert_one(amedasnew.model_dump(by_alias=True))
            if result.inserted_id:
                logger.info(f"Inserted {result.inserted_id} records")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to create sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
        return False

    @staticmethod
    async def get_sensor_data_latest():
        try:
            latest = await db.sensor_amedas.find_one(sort=[("timestamp", -1)])
            if latest:
                logger.info(f"Latest sensor data found: {latest}")
                return AmedasResponse(**latest)
            raise HTTPException(status_code=404, detail="amedas not found")
        except Exception as e:
            logger.error(f"Failed to get sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
