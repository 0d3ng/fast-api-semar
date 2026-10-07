import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.models.ota_end_device import EndDevice
from app.schemas.ota_end_device_schema import EndDeviceCreateUpdate, EndDeviceResponse
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
                ota_protocol=end_device.ota_protocol or "multicast",
                ip_address=end_device.ip_address,
                current_firmware_version=end_device.current_firmware_version,
                current_key_generation=end_device.current_key_generation or 1,
                status=end_device.status or "active",
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.ota_end_devices.insert_one(new_device.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            if new_id:
                return EndDeviceResponse(
                    _id=new_id,
                    code=new_device.code,
                    name=new_device.name,
                    description=new_device.description,
                    platform_type=new_device.platform_type,
                    edge_ota_id=new_device.edge_ota_id,
                    ota_protocol=new_device.ota_protocol,
                    ip_address=new_device.ip_address,
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
    async def _get_update_history_for_device(doc: dict) -> List[dict]:
        try:
            device_id_str = str(doc.get("_id"))
            device_code = doc.get("code")
            device_name = doc.get("name")
            identifiers = list(set(filter(None, [device_id_str, device_code, device_name])))

            ack_query = {
                "end_device_id": {"$in": identifiers},
                "deleted_at": None
            }
            acks = await db.ota_session_acks.find(ack_query).sort([("acked_at", -1), ("inserted_at", -1)]).to_list(length=100)

            history_list = []
            seen_session_keys = set()

            for ack in acks:
                session_ref = ack.get("update_session_id")
                session_doc = None
                is_rotation = False

                if session_ref:
                    session_query = {"deleted_at": None}
                    if ObjectId.is_valid(session_ref):
                        session_query["$or"] = [{"_id": ObjectId(session_ref)}, {"session_id": session_ref}]
                    else:
                        session_query["session_id"] = session_ref

                    session_doc = await db.ota_update_sessions.find_one(session_query)
                    if not session_doc:
                        session_doc = await db.ota_rotation_requests.find_one(session_query)
                        if session_doc:
                            is_rotation = True

                    if not session_doc and isinstance(session_ref, str) and session_ref.isdigit():
                        session_query_int = {"session_id": int(session_ref), "deleted_at": None}
                        session_doc = await db.ota_update_sessions.find_one(session_query_int)
                        if not session_doc:
                            session_doc = await db.ota_rotation_requests.find_one(session_query_int)
                            if session_doc:
                                is_rotation = True

                disp_session_id = str(session_doc.get("session_id") or session_doc.get("_id") or session_ref or "-") if session_doc else str(session_ref or "-")

                fw_version = "-"
                if session_doc:
                    seen_session_keys.add(str(session_doc.get("_id")))
                    if session_doc.get("target_version"):
                        fw_version = session_doc.get("target_version")
                    elif is_rotation or session_doc.get("new_key_generation"):
                        gen = session_doc.get("new_key_generation")
                        fw_version = f"Key Gen {gen}"
                    elif session_doc.get("firmware_release_id") and ObjectId.is_valid(session_doc.get("firmware_release_id")):
                        rel = await db.ota_firmware_releases.find_one({"_id": ObjectId(session_doc.get("firmware_release_id"))})
                        if rel and rel.get("version"):
                            fw_version = rel.get("version")

                ts_val = ack.get("acked_at") or ack.get("inserted_at")
                ts_str = ts_val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts_val, datetime) else str(ts_val or "-")

                history_list.append({
                    "session_id": disp_session_id,
                    "firmware_version": fw_version,
                    "status": ack.get("status") or "completed",
                    "timestamp": ts_str,
                    "_sort_ts": ts_val if isinstance(ts_val, datetime) else datetime.min
                })

            targeted_or = [
                {"target_device_ids": device_id_str},
                {"target_devices.device_id": device_id_str}
            ]
            if device_code:
                targeted_or.append({"target_devices.code": device_code})
            targeted_query = {
                "deleted_at": None,
                "$or": targeted_or
            }
            targeted_sessions = await db.ota_update_sessions.find(targeted_query).sort([("started_at", -1), ("inserted_at", -1)]).to_list(length=50)
            for tsess in targeted_sessions:
                sess_id_key = str(tsess.get("_id"))
                if sess_id_key not in seen_session_keys:
                    seen_session_keys.add(sess_id_key)
                    ts_val = tsess.get("completed_at") or tsess.get("started_at") or tsess.get("inserted_at")
                    ts_str = ts_val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts_val, datetime) else str(ts_val or "-")
                    history_list.append({
                        "session_id": str(tsess.get("session_id") or tsess.get("_id")),
                        "firmware_version": tsess.get("target_version") or "-",
                        "status": tsess.get("status") or "pending",
                        "timestamp": ts_str,
                        "_sort_ts": ts_val if isinstance(ts_val, datetime) else datetime.min
                    })

            history_list.sort(key=lambda x: x.get("_sort_ts") or datetime.min, reverse=True)
            for item in history_list:
                item.pop("_sort_ts", None)

            return history_list
        except Exception as e:
            logger.error(f"Error compiling update history for end device: {e}")
            return []

    @staticmethod
    async def get_end_device(end_device_id: str):
        try:
            doc = await db.ota_end_devices.find_one({"_id": ObjectId(end_device_id), "deleted_at": None})
            if doc:
                doc["update_history"] = await EndDeviceService._get_update_history_for_device(doc)
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
            doc = await db.ota_end_devices.find_one({"edge_ota_id": edge_ota_id, "deleted_at": None})
            if doc:
                doc["update_history"] = await EndDeviceService._get_update_history_for_device(doc)
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
        ota_protocol: Optional[str] = None,
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
            if ota_protocol:
                query["ota_protocol"] = ota_protocol
            if status:
                query["status"] = status

            devices = []
            cursor = db.ota_end_devices.find(query)
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
        ota_protocol: Optional[str] = None,
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
            if ota_protocol:
                query["ota_protocol"] = ota_protocol

            if outdated:
                # Find active key generation from rotation requests or firmware releases
                latest_release = await db.ota_firmware_releases.find_one(
                    {"deleted_at": None},
                    sort=[("key_generation", -1)]
                )
                active_key_gen = latest_release.get("key_generation", 1) if latest_release else 1
                query["current_key_generation"] = {"$lt": active_key_gen}

            devices = []
            cursor = db.ota_end_devices.find(query)
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
            result = await db.ota_end_devices.update_one({"_id": ObjectId(end_device_id), "deleted_at": None}, {"$set": update_data})
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
            result = await db.ota_end_devices.update_one({"_id": ObjectId(end_device_id)}, {"$set": update_data})
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

            return await db.ota_end_devices.count_documents(query)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
