import json
import traceback
from datetime import datetime

import httpx
import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.messaging.mqtt_publisher import publish_message
from app.models.rotation_request import RotationRequest
from app.schemas.rotation_request_schema import RotationRequestCreate, RotationRequestResponse, RotationRequestCicdCallback, CurrentKeyGenerationResponse
from app.schemas.token_schema import TokenData
from app.services.server_service import ServerService
from app.utils.config import (
    CICD_DISPATCH_MODE,
    GITHUB_DISPATCH_TOKEN,
    GITHUB_REPO_NAME,
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
                status="pending_cicd",
                requested_at=now_utc,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.rotation_requests.insert_one(new_req.model_dump(by_alias=True))
            new_id = str(inserted.inserted_id)

            # Trigger CI/CD dispatch
            if CICD_DISPATCH_MODE == "live":
                url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{GITHUB_WORKFLOW_ID}/dispatches"
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {GITHUB_DISPATCH_TOKEN}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
                payload = {
                    "ref": "main",
                    "inputs": {
                        "rotation_id": new_id,
                        "target_scope": req_data.target_scope
                    }
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code not in (200, 204):
                        logger.error(f"CI/CD dispatch failed: {resp.status_code} {resp.text}")
            else:
                logger.info(f"[STUB MODE] CI/CD key rotation dispatch triggered for rotation_id: {new_id}")

            doc = await db.rotation_requests.find_one({"_id": ObjectId(new_id)})
            return RotationRequestResponse(**doc)
        except Exception as e:
            logger.error(f"Failed to create rotation request: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_rotation_request(rotation_id: str):
        try:
            doc = await db.rotation_requests.find_one({"_id": ObjectId(rotation_id), "deleted_at": None})
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
            cursor = db.rotation_requests.find({"deleted_at": None})
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
            res = await db.rotation_requests.update_one(
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
            req = await db.rotation_requests.find_one({"_id": ObjectId(rotation_id), "deleted_at": None})
            if not req:
                raise HTTPException(status_code=404, detail="RotationRequest not found")

            if req["status"] not in ("ready_to_broadcast", "pending_cicd"):
                raise HTTPException(status_code=400, detail=f"Cannot broadcast request in status '{req['status']}'")

            # Update status to broadcasting
            await db.rotation_requests.update_one(
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
            doc = await db.rotation_requests.find_one(
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

