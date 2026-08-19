from app.utils.config import FIRMWARE_UPDATE_TOPIC
from app.utils.config import ENV
from app.utils.config import MESSAGE_BROKER
import json
import os
import time
import traceback
from datetime import datetime
from typing import Optional, List

import pytz
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.messaging.mqtt_publisher import publish_message
from app.models.firmware_release import FirmwareRelease
from app.schemas.firmware_release_schema import FirmwareReleaseCreate, FirmwareReleaseResponse, LatestFirmwareReleaseResponse
from app.schemas.token_schema import TokenData
from app.schemas.update_session_schema import UpdateSessionCreate
from app.services.edge_ota_service import EdgeOtaService
from app.services.end_device_service import EndDeviceService
from app.services.server_service import ServerService
from app.services.update_session_service import UpdateSessionService
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
    async def get_releases_by_target_and_platform(
        target_version: str,
        platform_type: Optional[str] = None
    ) -> List[FirmwareReleaseResponse]:
        try:
            query = {"target_version": target_version, "deleted_at": None}
            if platform_type:
                query["platform_type"] = platform_type
            releases = []
            cursor = db.firmware_releases.find(query)
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
                return LatestFirmwareReleaseResponse(
                    target_version=doc.get("target_version"),
                    base_version=doc.get("base_version"),
                    type=doc.get("type"),
                    platform_type=doc.get("platform_type"),
                    target_hash=doc.get("target_hash"),
                    delta_hash=doc.get("delta_hash"),
                    delta_algorithm=doc.get("delta_algorithm"),
                    delta_size=doc.get("delta_size"),
                    target_size=doc.get("target_size"),
                    key_generation=doc.get("key_generation"),
                    signature=doc.get("signature"),
                    download_url=doc.get("file_path")
                )

            return LatestFirmwareReleaseResponse()
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def broadcast_firmware(target_version: str, platform_type: str, user_id: str):
        try:
            # 1. Query firmware releases via service method
            releases = await FirmwareReleaseService.get_releases_by_target_and_platform(
                target_version=target_version,
                platform_type=platform_type
            )
            if not releases:
                raise HTTPException(status_code=404, detail="Firmware releases not found")

            # 2. Query active edge OTAs via EdgeOtaService
            edges = await EdgeOtaService.get_all_edge_otas(active=True)

            # 3. Get server config via ServerService
            server = await ServerService.get_server_config(MESSAGE_BROKER, environment=ENV)
            if not server:
                logger.warning("MQTT Server configuration not found")

            sessions_created = []
            sys_token = TokenData(user_id=user_id, username=user_id)

            for edge in edges:
                edge_id = str(edge.id)

                # 4. Count end devices via EndDeviceService
                device_count = await EndDeviceService.count_end_devices(
                    edge_ota_id=edge_id,
                    platform_type=platform_type
                )

                if device_count > 0:
                    for release in releases:
                        release_type = release.type
                        session_id = str(int(time.time()))

                        # 5. Insert UpdateSession via UpdateSessionService
                        session_data = UpdateSessionCreate(
                            session_id=session_id,
                            type=release_type,
                            firmware_release_id=str(release.id),
                            target_edge_ota_id=edge_id,
                            status="preparing"
                        )

                        await UpdateSessionService.create_session(session_data, sys_token)

                        sessions_created.append({
                            "session_id": int(session_id),
                            "edge_id": edge_id,
                            "type": release_type,
                            "device_count": device_count
                        })

                        # 6. Publish MQTT message
                        if server:
                            payload = json.dumps({
                                "session_id": session_id,
                                "type": release_type,
                                "target_version": target_version,
                                "target_edge_ota_id": edge_id
                            })
                            publish_message(topic=FIRMWARE_UPDATE_TOPIC, payload=payload, qos=server.parameters['qos'], server=server)

                        time.sleep(1)

            return {
                "target_version": target_version,
                "platform_type": platform_type,
                "sessions_created": sessions_created
            }
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

