#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-05 00:41:25
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-05 00:41:25
#  File: device_service.py
#  Description:
#  """
import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.messaging.mqtt_publisher import publish_message
from app.models.device import Device
from app.schemas.device_schema import DeviceCreateUpdate, DeviceResponse
from app.utils.config import MQTT_TOPIC_DEVICE_UNSUB
from app.utils.db import db
from app.utils.generator import generate_random_alphanumeric_hexa
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class DeviceService:
    @staticmethod
    async def create_device(device: DeviceCreateUpdate, current_user: str):
        try:
            logger.info(device)
            new_device: Device = Device(
                code=generate_random_alphanumeric_hexa(),
                name=device.name,
                description=device.description,
                type=device.type,
                protocol=device.protocol,
                project_id=device.project_id,
                active=device.active,
                inserted_at=datetime_jpn,
                inserted_by=current_user
            )
            logger.info(new_device)
            new_device_inserted = await db.devices.insert_one(new_device.model_dump(by_alias=True))
            new_device_id = new_device_inserted.inserted_id
            logger.info(f"{new_device_id} {type(new_device_id)}")
            return DeviceResponse(_id=new_device_id,
                                  code=new_device.code,
                                  name=device.name,
                                  description=device.description,
                                  type=device.type,
                                  protocol=device.protocol,
                                  project_id=device.project_id,
                                  active=device.active,
                                  inserted_at=datetime_jpn,
                                  inserted_by=current_user)
        except Exception as e:
            logger.error(f"Failed to create device: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_device(device_id: str):
        try:
            project = await db.devices.find_one({"_id": ObjectId(device_id)})
            if project:
                return DeviceResponse(**project)
            raise HTTPException(status_code=404, detail="Device not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_devices():
        try:
            projects = []
            cursor = db.devices.find({})
            async for project in cursor:
                logger.info(f"{project} {project["_id"]}")
                project_response = DeviceResponse(**project)
                projects.append(project_response)
                logger.info("")
            return projects
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_active_all_devices(protocol):
        try:
            projects = []
            cursor = db.devices.find({
                "active": True,
                "deleted_at": {"$eq": None},
                "protocol": {"$eq": protocol}
            })
            async for project in cursor:
                # logger.info(f"{project} {project["_id"]}")
                project_response = DeviceResponse(**project)
                projects.append(project_response)
                logger.info("")
            return projects
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_device(device_id: str, device_update: DeviceCreateUpdate, current_user: str):
        try:
            update_data = {k: v for k, v in device_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            result = await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await DeviceService.get_device(device_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_device(device_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": update_data})
            if result.matched_count == 1:
                device = await db.devices.find_one({"_id": ObjectId(device_id)})
                if device:
                    publish_message((MQTT_TOPIC_DEVICE_UNSUB + device.code), device.code, qos=1)
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
