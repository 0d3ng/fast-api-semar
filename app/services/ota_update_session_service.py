import traceback
from datetime import datetime

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.models.ota_session_ack import SessionAck
from app.models.ota_update_session import UpdateSession
from app.schemas.ota_session_ack_schema import SessionAckCreate, SessionAckResponse
from app.schemas.token_schema import TokenData
from app.schemas.ota_update_session_schema import UpdateSessionCreate, UpdateSessionResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UpdateSessionService:
    @staticmethod
    async def create_session(session_data: UpdateSessionCreate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            new_session: UpdateSession = UpdateSession(
                session_id=str(session_data.session_id),
                type=session_data.type,
                platform_type=session_data.platform_type,
                target_version=session_data.target_version,
                firmware_release_id=session_data.firmware_release_id,
                rotation_request_id=session_data.rotation_request_id,
                target_edge_ota_id=session_data.target_edge_ota_id,
                target_device_ids=session_data.target_device_ids,
                status=session_data.status or "preparing",
                started_at=now_utc,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.ota_update_sessions.insert_one(new_session.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            if new_id:
                return UpdateSessionResponse(
                    _id=new_id,
                    session_id=new_session.session_id,
                    type=new_session.type,
                    firmware_release_id=new_session.firmware_release_id,
                    rotation_request_id=new_session.rotation_request_id,
                    target_edge_ota_id=new_session.target_edge_ota_id,
                    status=new_session.status,
                    started_at=now_utc,
                    inserted_at=now_utc,
                    inserted_by=current_user.user_id
                )
            raise HTTPException(status_code=500, detail="Insert update session failed")
        except Exception as e:
            logger.error(f"Failed to create update session: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_session(session_id: str):
        try:
            query = {"deleted_at": None}
            if ObjectId.is_valid(session_id):
                query["$or"] = [{"_id": ObjectId(session_id)}, {"session_id": session_id}]
            else:
                query["session_id"] = session_id

            doc = await db.ota_update_sessions.find_one(query)
            if doc:
                return UpdateSessionResponse(**doc)
            raise HTTPException(status_code=404, detail="UpdateSession not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_sessions():
        try:
            sessions = []
            cursor = db.ota_update_sessions.find({"deleted_at": None})
            async for doc in cursor:
                sessions.append(UpdateSessionResponse(**doc))
            return sessions
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_pending_sessions(edge_id: str, target_version: str):
        try:
            from app.services.ota_firmware_release_service import FirmwareReleaseService
            from app.services.ota_edge_service import EdgeOtaService
            from app.services.ota_end_device_service import EndDeviceService

            # 1. Resolve edge identifier via EdgeOtaService
            target_edge_ids = [edge_id]
            edge_obj = None
            try:
                edge_obj = await EdgeOtaService.get_edge_ota(edge_id)
                if edge_obj:
                    target_edge_ids.append(str(edge_obj.id))
                    if edge_obj.code:
                        target_edge_ids.append(edge_obj.code)
            except HTTPException:
                pass
            target_edge_ids = list(set(target_edge_ids))

            # 2. Find releases matching target_version via FirmwareReleaseService
            releases = await FirmwareReleaseService.get_releases_by_target_and_platform(
                target_version=target_version
            )
            if not releases:
                return {"sessions": []}

            release_map = {str(r.id): r for r in releases}
            release_ids = list(release_map.keys())

            # 3. Find pending update sessions for this edge and target releases
            sessions_query = {
                "target_edge_ota_id": {"$in": target_edge_ids},
                "status": {"$in": ["pending", "preparing"]},
                "firmware_release_id": {"$in": release_ids},
                "deleted_at": None
            }
            sessions_cursor = db.ota_update_sessions.find(sessions_query)
            sessions = []
            async for s in sessions_cursor:
                sessions.append(s)

            result_sessions = []
            for session in sessions:
                release_doc = release_map.get(session.get("firmware_release_id"))
                if not release_doc:
                    continue

                raw_session_id = session.get("session_id")
                try:
                    session_id_val = int(raw_session_id)
                except (ValueError, TypeError):
                    session_id_val = raw_session_id

                manifest = {
                    "target_version": release_doc.target_version,
                    "base_version": release_doc.base_version,
                    "type": release_doc.type,
                    "platform_type": release_doc.platform_type,
                    "target_hash": release_doc.target_hash,
                    "delta_hash": release_doc.delta_hash,
                    "delta_algorithm": release_doc.delta_algorithm,
                    "delta_size": release_doc.delta_size,
                    "target_size": release_doc.target_size,
                    "key_generation": release_doc.key_generation,
                    "signature": release_doc.signature,
                    "file_path":release_doc.file_name
                }
                manifest = {k: v for k, v in manifest.items() if v is not None}

                # 4. Fetch target device IDs via EndDeviceService or existing session field
                if session.get("target_device_ids"):
                    target_device_ids = session.get("target_device_ids")
                else:
                    target_edge_key = str(edge_obj.id) if (edge_obj and edge_obj.id) else edge_id
                    devices = await EndDeviceService.get_end_devices(
                        edge_ota_id=target_edge_key,
                        platform_type=release_doc.platform_type
                    )

                    if release_doc.type == "delta" and release_doc.base_version:
                        matched_devices = [
                            d for d in devices
                            if d.current_firmware_version == release_doc.base_version
                        ]
                        if matched_devices:
                            devices = matched_devices

                    target_device_ids = [
                        str(d.code or d.id) for d in devices
                    ]

                result_sessions.append({
                    "session_id": session_id_val,
                    "type": session.get("type") or release_doc.type,
                    "manifest": manifest,
                    "target_device_ids": target_device_ids
                })

            return {"sessions": result_sessions}
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_session_status(session_id: str, new_status: str, user_id: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            query = {"deleted_at": None}
            if ObjectId.is_valid(session_id):
                query["$or"] = [{"_id": ObjectId(session_id)}, {"session_id": session_id}]
            else:
                query["session_id"] = session_id

            session = await db.ota_update_sessions.find_one(query)
            if not session:
                raise HTTPException(status_code=404, detail="UpdateSession not found")

            update_fields = {
                "status": new_status,
                "updated_at": now_utc,
                "updated_by": user_id
            }

            await db.ota_update_sessions.update_one(
                {"_id": session["_id"]},
                {"$set": update_fields}
            )

            # If session marked as completed, update end devices firmware version & key generation
            if new_status == "completed" and session.get("target_device_ids"):
                device_ids = session.get("target_device_ids")
                object_ids = [ObjectId(d) for d in device_ids if ObjectId.is_valid(d)]
                codes = [d for d in device_ids if not ObjectId.is_valid(d)]

                device_query_or = []
                if object_ids:
                    device_query_or.append({"_id": {"$in": object_ids}})
                if codes:
                    device_query_or.append({"code": {"$in": codes}})

                if device_query_or:
                    device_update = {
                        "last_update_at": now_utc,
                        "updated_at": now_utc,
                        "updated_by": user_id
                    }
                    if session.get("target_version"):
                        device_update["current_firmware_version"] = session.get("target_version")

                    if session.get("firmware_release_id") and ObjectId.is_valid(session.get("firmware_release_id")):
                        release_doc = await db.ota_firmware_releases.find_one({"_id": ObjectId(session.get("firmware_release_id"))})
                        if release_doc and release_doc.get("key_generation") is not None:
                            device_update["current_key_generation"] = release_doc.get("key_generation")

                    if session.get("rotation_request_id") and ObjectId.is_valid(session.get("rotation_request_id")):
                        rotation_doc = await db.ota_rotation_requests.find_one({"_id": ObjectId(session.get("rotation_request_id"))})
                        if rotation_doc and rotation_doc.get("new_key_generation") is not None:
                            device_update["current_key_generation"] = rotation_doc.get("new_key_generation")

                    await db.ota_end_devices.update_many(
                        {"deleted_at": None, "$or": device_query_or},
                        {"$set": device_update}
                    )

            updated_doc = await db.ota_update_sessions.find_one({"_id": session["_id"]})
            return UpdateSessionResponse(**updated_doc)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def add_session_ack(session_id: str, ack_data: SessionAckCreate, user_id: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            query = {"deleted_at": None}
            if ObjectId.is_valid(session_id):
                query["$or"] = [{"_id": ObjectId(session_id)}, {"session_id": session_id}]
            else:
                query["session_id"] = session_id

            session = await db.ota_update_sessions.find_one(query)
            if not session:
                raise HTTPException(status_code=404, detail="UpdateSession not found")

            new_ack: SessionAck = SessionAck(
                update_session_id=str(session["_id"]),
                end_device_id=ack_data.end_device_id,
                acked_at=now_utc,
                status=ack_data.status,
                notes=ack_data.notes,
                inserted_at=now_utc,
                inserted_by=user_id
            )
            inserted = await db.ota_session_acks.insert_one(new_ack.model_dump(by_alias=True))
            new_id = inserted.inserted_id

            if new_id:
                # Update EndDevice last_update_at and current_firmware_version if status success
                if ack_data.status == "success":
                    device_update = {
                        "last_update_at": now_utc,
                        "updated_at": now_utc,
                        "updated_by": user_id
                    }
                    if session.get("target_version"):
                        device_update["current_firmware_version"] = session.get("target_version")

                    if session.get("firmware_release_id") and ObjectId.is_valid(session.get("firmware_release_id")):
                        release_doc = await db.ota_firmware_releases.find_one({"_id": ObjectId(session.get("firmware_release_id"))})
                        if release_doc and release_doc.get("key_generation") is not None:
                            device_update["current_key_generation"] = release_doc.get("key_generation")

                    if session.get("rotation_request_id") and ObjectId.is_valid(session.get("rotation_request_id")):
                        rotation_doc = await db.ota_rotation_requests.find_one({"_id": ObjectId(session.get("rotation_request_id"))})
                        if rotation_doc and rotation_doc.get("new_key_generation") is not None:
                            device_update["current_key_generation"] = rotation_doc.get("new_key_generation")

                    device_query = {"deleted_at": None}
                    if ObjectId.is_valid(ack_data.end_device_id):
                        device_query["$or"] = [{"_id": ObjectId(ack_data.end_device_id)}, {"code": ack_data.end_device_id}]
                    else:
                        device_query["code"] = ack_data.end_device_id

                    await db.ota_end_devices.update_one(
                        device_query,
                        {"$set": device_update}
                    )

                return SessionAckResponse(
                    _id=new_id,
                    update_session_id=str(session["_id"]),
                    end_device_id=ack_data.end_device_id,
                    acked_at=now_utc,
                    status=ack_data.status,
                    notes=ack_data.notes,
                    inserted_at=now_utc,
                    inserted_by=user_id
                )
            raise HTTPException(status_code=500, detail="Insert session ack failed")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add session ack: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
