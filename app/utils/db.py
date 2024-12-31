#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:47:25
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-11-27 22:54:07
#  File: db.py
#  Description:
#  """

from motor.motor_asyncio import AsyncIOMotorClient

from app.utils.config import MONGO_USER, MONGO_PASS, MONGO_HOST, MONGO_PORT, MONGO_DB
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    _client = None

    @staticmethod
    def get_client():
        if Database._client is None:
            try:
                Database._client = AsyncIOMotorClient(
                    f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
                )
                logger.info("Connected to MongoDB")
            except Exception as e:
                logger.error(f"Could not connect to MongoDB: {e}")
                raise e
        return Database._client


db = Database.get_client()[MONGO_DB]
