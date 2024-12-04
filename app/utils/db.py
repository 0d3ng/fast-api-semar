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
from dotenv import load_dotenv
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)
load_dotenv()


class Database:
    _client = None

    @staticmethod
    def get_client():
        if Database._client is None:
            try:
                Database._client = AsyncIOMotorClient(
                    f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"
                )
                logger.info("Connected to MongoDB")
            except Exception as e:
                logger.error(f"Could not connect to MongoDB: {e}")
                raise e
        return Database._client


db = Database.get_client()[os.getenv('MONGO_DB')]
