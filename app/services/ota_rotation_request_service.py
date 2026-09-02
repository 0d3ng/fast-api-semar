import json
import traceback
from datetime import datetime

import httpx
import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.messaging.mqtt_publisher import publish_message
from app.models.ota_rotation_request import RotationRequest
from app.schemas.ota_rotation_request_schema import RotationRequestCreate, RotationRequestResponse, RotationRequestCicdCallback, CurrentKeyGenerationResponse
from app.schemas.token_schema import TokenData
from app.services.server_service import ServerService
from app.utils.config import (
    CICD_DISPATCH_MODE,
    GITHUB_BRANCH,
    GITHUB_DISPATCH_TOKEN,
    GITHUB_REPO_NAME,
    GITHUB_REPO_NAMES,
    GITHUB_REPO_OWNER,
    GITHUB_WORKFLOW_ID,
    MESSAGE_BROKER,
)
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RotationRequestService:
    @staticmethod
    async def create_rotation_request(req_data: RotationRequestCreate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            new_req: RotationRequest = RotationRequest(
                trigger_type=req_data.trigger_type,
                requested_by=current_user.user_id,
                target_scope=req_data.target_scope,
                edge_id=req_data.edge_id,
                reason=req_data.reason,
                status="pending_cicd",
                requested_at=now_utc,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.ota_rotation_requests.insert_one(new_req.model_dump(by_alias=True))
            new_id = str(inserted.inserted_id)

            # Trigger CI/CD dispatch
            if CICD_DISPATCH_MODE == "live":
                url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{GITHUB_WORKFLOW_ID}/dispatches"
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {GITHUB_DISPATCH_TOKEN}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
                # Format target repos with owner if missing
                formatted_repos = [
                    f"{GITHUB_REPO_OWNER}/{r}" if "/" not in r else r
                    for r in GITHUB_REPO_NAMES
                ]
                payload = {
                    "ref": GITHUB_BRANCH,
                    "inputs": {
                        "rotation_id": new_id,
                        "target_scope": req_data.target_scope,
                        "target_repos": ",".join(formatted_repos)
                    }
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code not in (200, 204):
                        error_msg = f"CI/CD dispatch failed ({resp.status_code}): {resp.text}"
                        logger.error(error_msg)
                        await db.ota_rotation_requests.update_one(
                            {"_id": ObjectId(new_id)},
                            {"$set": {"status": "failed", "updated_at": datetime.now(tz=pytz.UTC)}}
                        )
                        raise HTTPException(status_code=502, detail=error_msg)
            else:
                logger.info(f"[STUB MODE] CI/CD key rotation dispatch triggered for rotation_id: {new_id}")

            doc = await db.ota_rotation_requests.find_one({"_id": ObjectId(new_id)})
            return RotationRequestResponse(**doc)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create rotation request: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_rotation_request(rotation_id: str):
        try:
            doc = await db.ota_rotation_requests.find_one({"_id": ObjectId(rotation_id), "deleted_at": None})
            if doc:
                return RotationRequestResponse(**doc)
            raise HTTPException(status_code=404, detail="RotationRequest not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_rotation_requests():
        try:
            reqs = []
            cursor = db.ota_rotation_requests.find({"deleted_at": None})
            async for doc in cursor:
                reqs.append(RotationRequestResponse(**doc))
            return reqs
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def handle_cicd_callback(rotation_id: str, callback_data: RotationRequestCicdCallback):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            update_fields = {
                "new_key_generation": callback_data.new_key_generation,
                "signed_manifest": callback_data.signed_manifest,
                "status": "ready_to_broadcast",
                "signed_at": now_utc,
                "updated_at": now_utc,
                "updated_by": "cicd_webhook"
            }
            res = await db.ota_rotation_requests.update_one(
                {"_id": ObjectId(rotation_id), "deleted_at": None},
                {"$set": update_fields}
            )
            if res.matched_count == 1:
                return await RotationRequestService.get_rotation_request(rotation_id)
            raise HTTPException(status_code=404, detail="RotationRequest not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def broadcast_rotation(rotation_id: str, user_id: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            req = await db.ota_rotation_requests.find_one({"_id": ObjectId(rotation_id), "deleted_at": None})
            if not req:
                raise HTTPException(status_code=404, detail="RotationRequest not found")

            if req["status"] not in ("ready_to_broadcast", "pending_cicd"):
                raise HTTPException(status_code=400, detail=f"Cannot broadcast request in status '{req['status']}'")

            # Update status to broadcasting
            await db.ota_rotation_requests.update_one(
                {"_id": ObjectId(rotation_id)},
                {"$set": {"status": "broadcasting", "broadcast_at": now_utc, "updated_at": now_utc, "updated_by": user_id}}
            )

            # Stub / MQTT publish command to Edge devices
            try:
                server = await ServerService.get_server_config(protocol=MESSAGE_BROKER.lower(), environment="development")
                if server:
                    topic = "device/ota/rotation"
                    payload = json.dumps({
                        "rotation_id": rotation_id,
                        "new_key_generation": req.get("new_key_generation"),
                        "signed_manifest": req.get("signed_manifest")
                    })
                    publish_message(topic=topic, payload=payload, qos=1, server=server)
            except Exception as mqtt_err:
                logger.warning(f"MQTT publish failed or stubbed: {mqtt_err}")

            return await RotationRequestService.get_rotation_request(rotation_id)
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_current_key_generation():
        try:
            doc = await db.ota_rotation_requests.find_one(
                {"new_key_generation": {"$ne": None}, "deleted_at": None},
                sort=[("new_key_generation", -1)]
            )
            if doc and "new_key_generation" in doc and doc["new_key_generation"] is not None:
                return CurrentKeyGenerationResponse(key_generation=doc["new_key_generation"])
            return CurrentKeyGenerationResponse(key_generation=0)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def add_rotation_ack(rotation_id: str, device_id: str, success: bool = True):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            if not ObjectId.is_valid(rotation_id):
                logger.warning(f"Invalid rotation_id for ACK: {rotation_id}")
                return False

            req = await db.ota_rotation_requests.find_one({"_id": ObjectId(rotation_id), "deleted_at": None})
            if not req:
                logger.warning(f"RotationRequest not found for ACK: {rotation_id}")
                return False

            if success:
                await db.ota_rotation_requests.update_one(
                    {"_id": ObjectId(rotation_id)},
                    {
                        "$addToSet": {"acknowledged_by": device_id},
                        "$pull": {"failed_on": device_id},
                        "$set": {"updated_at": now_utc, "updated_by": "device_ack"}
                    }
                )
                new_key_gen = req.get("new_key_generation")
                if new_key_gen is not None:
                    device_query = {"deleted_at": None}
                    if ObjectId.is_valid(device_id):
                        device_query["_id"] = ObjectId(device_id)
                    else:
                        device_query["device_code"] = device_id

                    await db.ota_end_devices.update_one(
                        device_query,
                        {
                            "$set": {
                                "current_key_generation": new_key_gen,
                                "updated_at": now_utc,
                                "updated_by": "rotation_ack"
                            }
                        }
                    )
                logger.info(f"Recorded successful rotation ACK for device {device_id} on rotation {rotation_id}")
            else:
                await db.ota_rotation_requests.update_one(
                    {"_id": ObjectId(rotation_id)},
                    {
                        "$addToSet": {"failed_on": device_id},
                        "$pull": {"acknowledged_by": device_id},
                        "$set": {"updated_at": now_utc, "updated_by": "device_ack"}
                    }
                )
                logger.info(f"Recorded failed rotation ACK for device {device_id} on rotation {rotation_id}")

            return True
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"Failed to add rotation ACK: {e}\n{tb_str}")
            return False


