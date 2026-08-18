import os
import traceback
from datetime import datetime
from typing import Optional

import pytz
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.models.firmware_release import FirmwareRelease
from app.schemas.firmware_release_schema import FirmwareReleaseCreate, FirmwareReleaseResponse, LatestFirmwareReleaseResponse
from app.schemas.token_schema import TokenData
from app.utils.config import FIRMWARE_FOLDER
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FirmwareReleaseService:
    @staticmethod
    async def create_release(
        release_data: FirmwareReleaseCreate,
        file: Optional[UploadFile] = None,
        user_id: Optional[str] = "system"
    ):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            saved_file_path = None

            if file:
                storage_dir = os.path.join(FIRMWARE_FOLDER, "ota")
                os.makedirs(storage_dir, exist_ok=True)
                file_name = f"{release_data.target_version}_{release_data.type}_{file.filename}"
                saved_file_path = os.path.join(storage_dir, file_name)

                content = await file.read()
                with open(saved_file_path, "wb") as f:
                    f.write(content)

            new_release: FirmwareRelease = FirmwareRelease(
                target_version=release_data.target_version,
                base_version=release_data.base_version,
                type=release_data.type,
                platform_type=release_data.platform_type,
                target_hash=release_data.target_hash,
                delta_hash=release_data.delta_hash,
                delta_algorithm=release_data.delta_algorithm,
                delta_size=release_data.delta_size,
                target_size=release_data.target_size,
                key_generation=release_data.key_generation,
                signature=release_data.signature,
                file_path=file_name,
                inserted_at=now_utc,
                inserted_by=user_id
            )
            inserted = await db.firmware_releases.insert_one(new_release.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            if new_id:
                return FirmwareReleaseResponse(
                    _id=new_id,
                    target_version=new_release.target_version,
                    base_version=new_release.base_version,
                    type=new_release.type,
                    platform_type=new_release.platform_type,
                    target_hash=new_release.target_hash,
                    delta_hash=new_release.delta_hash,
                    delta_algorithm=new_release.delta_algorithm,
                    delta_size=new_release.delta_size,
                    target_size=new_release.target_size,
                    key_generation=new_release.key_generation,
                    signature=new_release.signature,
                    download_url=saved_file_path,
                    inserted_at=now_utc,
                    inserted_by=user_id
                )
            raise HTTPException(status_code=500, detail="Insert firmware release failed")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create firmware release: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_release(release_id: str):
        try:
            doc = await db.firmware_releases.find_one({"_id": ObjectId(release_id), "deleted_at": None})
            if doc:
                return FirmwareReleaseResponse(**doc)
            raise HTTPException(status_code=404, detail="Firmware release not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_releases():
        try:
            releases = []
            cursor = db.firmware_releases.find({"deleted_at": None})
            async for doc in cursor:
                releases.append(FirmwareReleaseResponse(**doc))
            return releases
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_latest_release(release_type: Optional[str] = None, platform_type: Optional[str] = None):
        try:
            query = {"deleted_at": None}
            if release_type:
                query["type"] = release_type
            if platform_type:
                query["platform_type"] = platform_type

            doc = await db.firmware_releases.find_one(query, sort=[("inserted_at", -1)])
            if doc:
                inserted_at = doc.get("inserted_at")
                if isinstance(inserted_at, datetime):
                    created_at_str = inserted_at.isoformat()
                else:
                    created_at_str = inserted_at

                return LatestFirmwareReleaseResponse(
                    target_version=doc.get("target_version"),
                    type=doc.get("type"),
                    platform_type=doc.get("platform_type"),
                    target_hash=doc.get("target_hash"),
                    download_url=doc.get("file_path"),
                    created_at=created_at_str
                )

            return LatestFirmwareReleaseResponse(
                target_version=None,
                type=None,
                platform_type=None,
                target_hash=None,
                download_url=None,
                created_at=None
            )
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

