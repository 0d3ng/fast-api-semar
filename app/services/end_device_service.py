import traceback
from datetime import datetime
from typing import Optional, List

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.models.end_device import EndDevice
from app.schemas.end_device_schema import EndDeviceCreateUpdate, EndDeviceResponse
from app.schemas.token_schema import TokenData
from app.utils.db import db
from app.utils.generator import generate_random_alphanumeric_hexa
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EndDeviceService:
    @staticmethod
    async def create_end_device(end_device: EndDeviceCreateUpdate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            new_device: EndDevice = EndDevice(
                code=generate_random_alphanumeric_hexa(),
                name=end_device.name,
                description=end_device.description,
                platform_type=end_device.platform_type,
                edge_ota_id=end_device.edge_ota_id,
                current_firmware_version=end_device.current_firmware_version,
                current_key_generation=end_device.current_key_generation or 1,
                status=end_device.status or "active",
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.end_devices.insert_one(new_device.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            if new_id:
                return EndDeviceResponse(
                    _id=new_id,
                    code=new_device.code,
                    name=new_device.name,
                    description=new_device.description,
                    platform_type=new_device.platform_type,
                    edge_ota_id=new_device.edge_ota_id,
                    current_firmware_version=new_device.current_firmware_version,
                    current_key_generation=new_device.current_key_generation,
                    status=new_device.status,
                    inserted_at=now_utc,
                    inserted_by=current_user.user_id
                )
            raise HTTPException(status_code=500, detail="Insert end_device failed")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create end_device: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_end_device(end_device_id: str):
        try:
            doc = await db.end_devices.find_one({"_id": ObjectId(end_device_id), "deleted_at": None})
            if doc:
                return EndDeviceResponse(**doc)
            raise HTTPException(status_code=404, detail="EndDevice not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_end_device_by_edge_ota_id(edge_ota_id: str):
        try:
            doc = await db.end_devices.find_one({"edge_ota_id": edge_ota_id, "deleted_at": None})
            if doc:
                return EndDeviceResponse(**doc)
            raise HTTPException(status_code=404, detail="EndDevice with given edge_ota_id not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))


    @staticmethod
    async def get_end_devices(
        edge_ota_id: Optional[str] = None,
        platform_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[EndDeviceResponse]:
        try:
            query = {"deleted_at": None}
            if user_id:
                query["inserted_by"] = user_id
            if edge_ota_id:
                query["edge_ota_id"] = edge_ota_id
            if platform_type:
                query["platform_type"] = platform_type
            if status:
                query["status"] = status

            devices = []
            cursor = db.end_devices.find(query)
            async for doc in cursor:
                devices.append(EndDeviceResponse(**doc))
            return devices
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_end_devices(
        platform_type: Optional[str] = None,
        edge_ota_id: Optional[str] = None,
        outdated: Optional[bool] = None,
        user_id: Optional[str] = None
    ):
        try:
            query = {"deleted_at": None}
            if user_id:
                query["inserted_by"] = user_id
            if platform_type:
                query["platform_type"] = platform_type
            if edge_ota_id:
                query["edge_ota_id"] = edge_ota_id

            if outdated:
                # Find active key generation from rotation requests or firmware releases
                latest_release = await db.firmware_releases.find_one(
                    {"deleted_at": None},
                    sort=[("key_generation", -1)]
                )
                active_key_gen = latest_release.get("key_generation", 1) if latest_release else 1
                query["current_key_generation"] = {"$lt": active_key_gen}

            devices = []
            cursor = db.end_devices.find(query)
            async for doc in cursor:
                devices.append(EndDeviceResponse(**doc))
            return devices
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_end_device(end_device_id: str, update_data_in: EndDeviceCreateUpdate, current_user: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            update_data = {k: v for k, v in update_data_in.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = now_utc
            update_data["updated_by"] = current_user
            result = await db.end_devices.update_one({"_id": ObjectId(end_device_id), "deleted_at": None}, {"$set": update_data})
            if result.matched_count == 1:
                return await EndDeviceService.get_end_device(end_device_id)
            return None
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_end_device(end_device_id: str, current_user: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            update_data = {
                "deleted_at": now_utc,
                "deleted_by": current_user
            }
            result = await db.end_devices.update_one({"_id": ObjectId(end_device_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def count_end_devices(
        edge_ota_id: Optional[str] = None,
        platform_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        try:
            query = {"deleted_at": None}
            if user_id:
                query["inserted_by"] = user_id
            if platform_type:
                query["platform_type"] = platform_type
            if edge_ota_id:
                query["edge_ota_id"] = edge_ota_id

            return await db.end_devices.count_documents(query)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
