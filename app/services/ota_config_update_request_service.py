import asyncio
import json
import traceback
from datetime import datetime
from typing import List, Optional

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.messaging.mqtt_publisher import publish_message
from app.models.ota_config_update_request import ConfigUpdateRequest
from app.schemas.ota_config_update_request_schema import (
    ConfigUpdateRequestCreate,
    ConfigUpdateRequestResponse,
    ConfigUpdateAckPayload,
)
from app.schemas.token_schema import TokenData
from app.services.server_service import ServerService
from app.utils.config import MESSAGE_BROKER
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigUpdateRequestService:
    _ack_lock = asyncio.Lock()

    @staticmethod
    async def create_config_request(req_data: ConfigUpdateRequestCreate, current_user: TokenData) -> ConfigUpdateRequestResponse:
        try:
            now_utc = datetime.now(tz=pytz.UTC)

            # Query target devices (only active devices)
            device_query = {
                "deleted_at": None,
                "status": {"$in": ["active", "online"]}
            }
            if req_data.target_scope == "all" and req_data.edge_id:
                device_query["edge_ota_id"] = str(req_data.edge_id)
            elif req_data.target_device_ids:
                valid_ids = [ObjectId(d) for d in req_data.target_device_ids if ObjectId.is_valid(d)]
                device_query["$or"] = [
                    {"_id": {"$in": valid_ids}},
                    {"code": {"$in": req_data.target_device_ids}}
                ]
            else:
                raise HTTPException(status_code=400, detail="No target devices specified")

            cursor = db.ota_end_devices.find(device_query)
            target_devices_info = []
            target_device_ids = []
            device_results = []

            async for d in cursor:
                dev_id_str = str(d["_id"])
                code = d.get("code") or dev_id_str
                target_device_ids.append(dev_id_str)
                proto = d.get("ota_protocol", "http") or "http"
                ip = d.get("ip_address") or ""

                target_devices_info.append({
                    "device_id": dev_id_str,
                    "code": code,
                    "name": d.get("name", ""),
                    "ip_address": ip,
                    "protocol": proto
                })

                device_results.append({
                    "device_id": dev_id_str,
                    "code": code,
                    "name": d.get("name", ""),
                    "ip_address": ip,
                    "protocol": proto,
                    "status": "pending",
                    "reason": None,
                    "updated_at": None
                })

            if not device_results:
                raise HTTPException(status_code=400, detail="No matching devices found for update request")

            clean_config = {k: v for k, v in req_data.config.model_dump(exclude_unset=True).items() if v is not None}

            new_req = ConfigUpdateRequest(
                target_scope=req_data.target_scope,
                edge_id=req_data.edge_id,
                target_device_ids=target_device_ids,
                config_payload=clean_config,
                status="in_progress",
                device_results=device_results,
                requested_by=current_user.user_id,
                requested_at=now_utc,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )

            inserted = await db.ota_config_update_requests.insert_one(new_req.model_dump(by_alias=True))
            new_id = str(inserted.inserted_id)

            # Publish to MQTT topic device/ota/config
            try:
                server = await ServerService.get_server_config(protocol=MESSAGE_BROKER.lower(), environment="development")
                if server:
                    topic = "device/ota/config"
                    payload = json.dumps({
                        "request_id": new_id,
                        "edge_id": req_data.edge_id,
                        "config": clean_config,
                        "target_devices": target_devices_info
                    })
                    publish_message(topic=topic, payload=payload, qos=1, server=server)
                    logger.info(f"Published config update request {new_id} to MQTT topic {topic}")
            except Exception as mqtt_err:
                logger.warning(f"MQTT publish failed: {mqtt_err}")

            return await ConfigUpdateRequestService.get_request_by_id(new_id)
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_requests() -> List[ConfigUpdateRequestResponse]:
        try:
            requests = []
            cursor = db.ota_config_update_requests.find({"deleted_at": None}).sort([("inserted_at", -1)])
            async for doc in cursor:
                requests.append(ConfigUpdateRequestResponse(**doc))
            return requests
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_request_by_id(request_id: str) -> ConfigUpdateRequestResponse:
        try:
            if not ObjectId.is_valid(request_id):
                raise HTTPException(status_code=400, detail="Invalid request ID")
            doc = await db.ota_config_update_requests.find_one({"_id": ObjectId(request_id), "deleted_at": None})
            if not doc:
                raise HTTPException(status_code=404, detail="Config update request not found")
            return ConfigUpdateRequestResponse(**doc)
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    async def record_device_ack(cls, request_id: str, ack_data: ConfigUpdateAckPayload) -> ConfigUpdateRequestResponse:
        async with cls._ack_lock:
            try:
                if not ObjectId.is_valid(request_id):
                    raise HTTPException(status_code=400, detail="Invalid request ID")

                doc = await db.ota_config_update_requests.find_one({"_id": ObjectId(request_id), "deleted_at": None})
                if not doc:
                    raise HTTPException(status_code=404, detail="Config update request not found")

                now_utc = datetime.now(tz=pytz.UTC)
                jst = pytz.timezone('Asia/Tokyo')
                now_jst = now_utc.astimezone(jst)
                now_str = now_jst.strftime('%Y-%m-%d %H:%M:%S')

                device_results = doc.get("device_results", [])
                updated = False
                matched_dev = None
                ack_id_norm = str(ack_data.device_id or "").strip().lower()

                for dev in device_results:
                    d_id = str(dev.get("device_id") or "").strip().lower()
                    d_code = str(dev.get("code") or "").strip().lower()
                    d_name = str(dev.get("name") or "").strip().lower()

                    if (
                        d_id == ack_id_norm
                        or d_code == ack_id_norm
                        or d_name == ack_id_norm
                        or len(device_results) == 1
                    ):
                        dev["status"] = ack_data.status
                        dev["reason"] = ack_data.reason
                        dev["updated_at"] = now_str
                        updated = True
                        matched_dev = dev
                        break

                if not updated:
                    # Add as extra device result if device not originally in list
                    device_results.append({
                        "device_id": ack_data.device_id,
                        "code": ack_data.device_id,
                        "status": ack_data.status,
                        "reason": ack_data.reason,
                        "updated_at": now_str
                    })

                # If ACK status is success, sync ota_protocol to ota_end_devices only if it was updated in this request
                config_payload = doc.get("config_payload", {})
                new_protocol = config_payload.get("ota_protocol")
                if ack_data.status == "success" and new_protocol:
                    new_protocol_clean = str(new_protocol).strip().lower()
                    query_or = []
                    if matched_dev:
                        if matched_dev.get("device_id") and ObjectId.is_valid(matched_dev.get("device_id")):
                            query_or.append({"_id": ObjectId(matched_dev["device_id"])})
                        if matched_dev.get("code"):
                            query_or.append({"code": matched_dev["code"]})
                        if matched_dev.get("name"):
                            query_or.append({"name": matched_dev["name"]})
                        matched_dev["protocol"] = new_protocol_clean

                    if ObjectId.is_valid(ack_data.device_id):
                        query_or.append({"_id": ObjectId(ack_data.device_id)})
                    else:
                        query_or.append({"code": ack_data.device_id})
                        query_or.append({"name": ack_data.device_id})

                    if query_or:
                        await db.ota_end_devices.update_one(
                            {"$or": query_or, "deleted_at": None},
                            {"$set": {"ota_protocol": new_protocol_clean, "updated_at": now_utc}}
                        )
                        logger.info(f"[CONFIG ACK] Synchronized ota_protocol='{new_protocol_clean}' to ota_end_devices for {ack_data.device_id}")

                # Check if all completed
                has_pending = any(d.get("status") == "pending" for d in device_results)
                new_status = doc.get("status", "in_progress")
                completed_at = doc.get("completed_at")

                if not has_pending:
                    success_count = sum(1 for d in device_results if d.get("status") == "success")
                    if success_count == len(device_results):
                        new_status = "completed"
                    elif success_count > 0:
                        new_status = "completed_partial"
                    else:
                        new_status = "failed"
                    completed_at = now_utc

                await db.ota_config_update_requests.update_one(
                    {"_id": ObjectId(request_id)},
                    {
                        "$set": {
                            "device_results": device_results,
                            "status": new_status,
                            "completed_at": completed_at,
                            "updated_at": now_utc
                        }
                    }
                )

                return await ConfigUpdateRequestService.get_request_by_id(request_id)
            except HTTPException:
                raise
            except Exception as e:
                tb_str = "".join(traceback.format_tb(e.__traceback__))
                logger.error(f"{e}\n{tb_str}")
                raise HTTPException(status_code=500, detail=str(e))
