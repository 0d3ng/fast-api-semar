#   """
#   Copyright (c) 2026 lepen - All Rights Reserved
#   Created by lepen on 2026-05-07 14:34:06
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2026-05-07 14:34:06
#   File: edge_data_service.py
#   Description:
#   """
import traceback
from datetime import datetime

import pytz
from fastapi import HTTPException
from passlib.context import CryptContext

from app.models.edge_data import EdgeData
from app.schemas.edge_data_schema import EdgeDataCreate, EdgeDataResponse
from app.schemas.token_schema import TokenDataDevice
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class EdgeDataService:
    @staticmethod
    async def create_edge_data(edge_data: EdgeDataCreate, token: TokenDataDevice):
        try:
            logger.info(edge_data)
            datetime_jpn = datetime.now(tz=pytz.UTC)
            timestamp_utc = edge_data.timestamp.astimezone(pytz.UTC)
            new_edge_data: EdgeData = EdgeData(
                edge_id=token.device_id,
                data=edge_data.data,
                timestamp=timestamp_utc,
                inserted_at=datetime_jpn,
                inserted_by=token.user_id
            )
            logger.info(new_edge_data)
            collection_name = "edge_data_" + token.device_code
            logger.info(collection_name)
            new_edge_data_inserted = await db[collection_name].insert_one(new_edge_data.model_dump(by_alias=True))
            new_edge_data_id = new_edge_data_inserted.inserted_id
            logger.info(f"{new_edge_data_id} {type(new_edge_data_id)}")
            return EdgeDataResponse(
                _id=new_edge_data_id,
                edge_id=token.device_id,
                data=edge_data.data,
                timestamp=edge_data.timestamp.isoformat(),
                inserted_at=datetime_jpn.isoformat(),
                inserted_by=token.user_id
            )
        except Exception as e:
            logger.error(f"Failed to create edge_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_edge_all_data(device_code: str):
        try:
            collection_name = "edge_data_" + device_code
            edge_data = []
            cursor = await db[collection_name].find({}).sort("timestamp", 1)
            async for sensor_data in cursor:
                edge_data.append(EdgeDataResponse(**sensor_data))
            if edge_data:
                return edge_data
            raise HTTPException(status_code=404, detail="Edge data not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_edge_last_data(device_code: str):
        try:
            collection_name = "edge_data_" + device_code
            sensor_data = await db[collection_name].find_one({}, sort=[("timestamp", -1)])
            if sensor_data:
                return EdgeDataResponse(**sensor_data)
            raise HTTPException(status_code=404, detail="Edge data not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
