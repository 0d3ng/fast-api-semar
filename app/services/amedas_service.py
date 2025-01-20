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
import asyncio
import traceback

from fastapi import HTTPException
from pymongo import UpdateOne

from app.schemas.amedas_schema import AmedasResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AmedasService:
    @staticmethod
    async def insert(document: list):
        try:
            result = await db["sensor_amedas"].insert_many(document)
            if result.inserted_id:
                logger.info(f"Inserted {len(result)} records")
                return {
                    "inserted: ": len(result),
                    "ids": result.inserted_ids
                }
            raise HTTPException(status_code=500, detail="Create amedas fail")
        except Exception as e:
            logger.error(f"Failed to create sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_sensor_data_latest():
        try:
            latest = await db["sensor_amedas"].find_one(sort=[("timestamp", -1)])
            if latest:
                logger.info(f"Latest sensor data found: {latest}")
                return AmedasResponse(**latest)
            raise HTTPException(status_code=404, detail="amedas not found")
        except Exception as e:
            logger.error(f"Failed to get sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
