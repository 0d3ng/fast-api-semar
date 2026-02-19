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
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.utils.config import MONGO_DB, MONGO_URL
from app.utils.logger import get_logger

logger = get_logger(__name__)

class Database:
    _client = None
    _db = None
    _init_lock = asyncio.Lock()

    @staticmethod
    async def init():
        async with Database._init_lock:
            if Database._client is not None:
                return Database._db
            try:
                client = AsyncIOMotorClient(MONGO_URL)
                await client.admin.command("ping")
                logger.info(f"Connected to MongoDB - {MONGO_URL}")
                Database._client = client
                Database._db = client[MONGO_DB]
                return Database._db
            except PyMongoError as e:
                logger.error(f"Could not connect to MongoDB - {MONGO_URL}: {e}")
                raise e

    @staticmethod
    def get_db():
        if Database._db is None:
            raise RuntimeError("Database not initialized. Call Database.init() first.")
        return Database._db

db = None
