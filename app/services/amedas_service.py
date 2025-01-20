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

from pymongo import UpdateOne

from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AmedasService:
    @staticmethod
    async def insert(document: list):
        try:
            bulk_operations = []
            for doc in document:
                bulk_operations.append(UpdateOne({
                    "timestamp": doc["timestamp"]},
                    {"$setOnInsert": {
                        "timestamp": doc["timestamp"],
                        "temperature": doc["temperature"],
                        "wind_direction": doc["wind_direction"],
                        "wind_speed": doc["wind_speed"],
                        "humidity": doc["humidity"],
                        "pressure": doc["pressure"]
                    }
                    }, upsert=True))
            if bulk_operations:
                result = await db["sensor_amedas"].bulk_write(bulk_operations)
                logger.info(f"Amedas inserted: {result.upserted_count}, updated: {result.modified_count}")
        except Exception as e:
            logger.error(f"Failed to create sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")

    @staticmethod
    async def create_index():
        collection = db["sensor_amedas"]
        indexes = await collection.index_information()
        name_index = "timestamp_amedas"
        if name_index not in indexes:
            await collection.create_index("timestamp", unique=True, name=name_index)
            logger.info("Index created")


# asyncio.run(AmedasService.create_index())
