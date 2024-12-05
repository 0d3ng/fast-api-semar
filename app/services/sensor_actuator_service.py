import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.models.sensor_actuator import SensorData
from app.schemas.sensor_actuator_schema import SensorActuatorCreate, SensorActuatorResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class SensorActuatorService:
    @staticmethod
    async def create_sensor_data(sensor_data: SensorActuatorCreate, current_user: str):
        try:
            logger.info(sensor_data)
            new_sensor_data: SensorData = SensorData(
                device_id=sensor_data.device_id,
                data=sensor_data.data,
                timestamp=sensor_data.timestamp,
                inserted_at=datetime_jpn,
                inserted_by=current_user
            )
            logger.info(new_sensor_data)
            collection_name = "sensor_data_" + sensor_data.device_code
            logger.info(collection_name)
            new_sensor_data_inserted = await db[collection_name].insert_one(new_sensor_data.model_dump(by_alias=True))
            new_sensor_data_id = new_sensor_data_inserted.inserted_id
            logger.info(f"{new_sensor_data_id} {type(new_sensor_data_id)}")
            return SensorActuatorResponse(
                _id=new_sensor_data_id,
                device_id=sensor_data.device_id,
                device_code=sensor_data.device_code,
                data=sensor_data.data,
                timestamp=sensor_data.timestamp,
                inserted_at=datetime_jpn,
                inserted_by=current_user
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
    async def update_sensor_data(sensor_data_id: str, sensor_data: SensorActuatorCreate,current_user: str):
        try:
            update_data = {k: v for k, v in sensor_data.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            collection_name = "sensor_data_" + sensor_data.device_code
            result = await db[collection_name].update_one({"_id": ObjectId(sensor_data_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await SensorActuatorService.get_sensor_data(sensor_data_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_sensor_data(sensor_data_id: str, device_code: str, current_user: str):
        try:
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
