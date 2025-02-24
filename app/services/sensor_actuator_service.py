import traceback
from datetime import datetime

import pytz
from anyio.abc import value
from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pymongo import DESCENDING

from app.models.sensor_actuator import SensorData
from app.schemas.sensor_actuator_schema import SensorActuatorCreate, SensorActuatorResponse, DataSource
from app.schemas.token_schema import TokenDataDevice
from app.utils.db import db
from app.utils.json_tools import extract_sensors, is_number
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SensorActuatorService:
    @staticmethod
    async def create_sensor_data(sensor_data: SensorActuatorCreate, token: TokenDataDevice):
        try:
            logger.info(sensor_data)
            datetime_jpn = datetime.now(tz=pytz.UTC)
            timestamp_utc = sensor_data.timestamp.astimezone(pytz.UTC)
            new_sensor_data: SensorData = SensorData(
                device_id=token.device_id,
                data=sensor_data.data,
                timestamp=timestamp_utc,
                inserted_at=datetime_jpn,
                inserted_by=token.user_id
            )
            logger.info(new_sensor_data)
            collection_name = "sensor_data_" + token.device_code
            logger.info(collection_name)
            new_sensor_data_inserted = await db[collection_name].insert_one(new_sensor_data.model_dump(by_alias=True))
            new_sensor_data_id = new_sensor_data_inserted.inserted_id
            logger.info(f"{new_sensor_data_id} {type(new_sensor_data_id)}")
            return SensorActuatorResponse(
                _id=new_sensor_data_id,
                device_id=token.device_id,
                device_code=token.device_code,
                data=extract_sensors(sensor_data.data),
                timestamp=sensor_data.timestamp.isoformat(),
                inserted_at=datetime_jpn.isoformat(),
                inserted_by=token.user_id
            )
        except Exception as e:
            logger.error(f"Failed to create sensor_data: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_sensor_data(sensor_data_id: str, device_code: str):
        try:
            collection_name = "sensor_data_" + device_code
            sensor_data = await db[collection_name].find_one({"_id": ObjectId(sensor_data_id)})
            if sensor_data:
                return SensorActuatorResponse(**sensor_data, device_code=device_code)
            raise HTTPException(status_code=404, detail="Sensor data not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_last_sensor_data(device_code: str):
        try:
            collection_name = "sensor_data_" + device_code
            sensor_data = await db[collection_name].find_one(sort=[("inserted_at", DESCENDING)])
            logger.info(f"sensor_data: {sensor_data}")
            logger.info(f"type data: {type(sensor_data['data'])}")
            if sensor_data:
                new_response: SensorActuatorResponse = SensorActuatorResponse(**sensor_data, device_code=device_code)
                data = extract_sensors(new_response.data)
                new_response.data = data
                logger.info(new_response)
                return new_response
            raise HTTPException(status_code=404, detail="Sensor data not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_sensor_datas(device_code: str):
        try:
            sensor_datas = []
            collection_name = "sensor_data_" + device_code
            cursor = db[collection_name].find({})
            async for sensor_data in cursor:
                logger.info(f"{sensor_data} {sensor_data["_id"]}")
                sensor_data_response = SensorActuatorResponse(**sensor_data, device_code=device_code)
                sensor_datas.append(sensor_data_response)
                logger.info("")
            return sensor_datas
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_data_sources(device_code: str, start: str = None, end: str = None, only_numbers: bool = False):
        try:
            utc_tz = pytz.timezone('UTC')
            filter = {}
            logger.info(f"Parameters: {device_code} {start} {end}")
            if start and end:
                start_date_tokyo = datetime.strptime(f"{start} 00:00:00", "%Y-%m-%d %H:%M:%S")
                end_date_tokyo = datetime.strptime(f"{end} 23:59:59", "%Y-%m-%d %H:%M:%S")
                start_date_utc = start_date_tokyo.astimezone(utc_tz)
                end_date_utc = end_date_tokyo.astimezone(utc_tz)
                filter = {
                    "timestamp": {
                        "$gte": start_date_utc,
                        "$lt": end_date_utc
                    }
                }
            data_sources = []
            collection_name = "sensor_data_" + device_code
            cursor = db[collection_name].find(filter)
            async for sensor_data in cursor:
                if only_numbers:
                    data = extract_sensors(sensor_data["data"])
                    json_data = {key: value for key, value in data.items() if is_number(value)}
                else:
                    json_data = extract_sensors(sensor_data["data"])

                data_source: DataSource = DataSource(
                    id=sensor_data["_id"],
                    data=json_data,
                    timestamp=sensor_data["timestamp"],
                    inserted_at=sensor_data["inserted_at"],
                )
                # logger.info(f"{data_source} {sensor_data["_id"]}")
                data_sources.append(data_source)
                # logger.info("")
            return data_sources

        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_sensor_data(sensor_data_id: str, sensor_data: SensorActuatorCreate, current_user: str):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            update_data = {k: v for k, v in sensor_data.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            collection_name = "sensor_data_" + sensor_data.device_code
            update_data.pop("device_code", None)
            result = await db[collection_name].update_one({"_id": ObjectId(sensor_data_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await SensorActuatorService.get_sensor_data(sensor_data_id, sensor_data.device_code)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_sensor_data(sensor_data_id: str, device_code: str, current_user: str):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            collection_name = "sensor_data_" + device_code
            result = await db[collection_name].update_one({"_id": ObjectId(sensor_data_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
