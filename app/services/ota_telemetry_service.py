import traceback
from datetime import datetime

import pytz
from fastapi import HTTPException

from app.models.ota_telemetry import OtaTelemetry
from app.schemas.ota_telemetry_schema import OtaTelemetryCreate, OtaTelemetryResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OtaTelemetryService:
    @staticmethod
    async def create_telemetry(telemetry_data: OtaTelemetryCreate, user_id: str = "mqtt_system"):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            ts = telemetry_data.timestamp or now_utc
            if ts.tzinfo is None:
                ts = pytz.UTC.localize(ts)
            else:
                ts = ts.astimezone(pytz.UTC)

            session_id = telemetry_data.session_id
            if not session_id and telemetry_data.metrics:
                if "rotation_id" in telemetry_data.metrics:
                    session_id = telemetry_data.metrics["rotation_id"]

            telemetry_type = telemetry_data.type
            if not telemetry_type:
                if telemetry_data.stage and telemetry_data.stage.startswith("rotation_"):
                    telemetry_type = "rolling_key"
                else:
                    telemetry_type = "firmware_update"

            new_telemetry = OtaTelemetry(
                session_id=session_id,
                device_id=telemetry_data.device_id,
                stage=telemetry_data.stage,
                type=telemetry_type,
                metrics=telemetry_data.metrics,
                timestamp=ts,
                inserted_at=now_utc,
                inserted_by=user_id
            )

            result = await db.ota_telemetries.insert_one(new_telemetry.model_dump(by_alias=True))
            logger.info(f"[OTA_TELEMETRY] Inserted telemetry id={result.inserted_id} for device={telemetry_data.device_id}, stage={telemetry_data.stage}, session_id={session_id}")

            # Intercept Key Rotation ACK stages
            if telemetry_data.stage in ("rotation_success", "rotation_ack", "rotation_completed"):
                from app.services.ota_rotation_request_service import RotationRequestService
                await RotationRequestService.add_rotation_ack(
                    rotation_id=session_id,
                    device_id=telemetry_data.device_id,
                    success=True
                )
            elif telemetry_data.stage in ("rotation_failed", "rotation_error"):
                from app.services.ota_rotation_request_service import RotationRequestService
                await RotationRequestService.add_rotation_ack(
                    rotation_id=session_id,
                    device_id=telemetry_data.device_id,
                    success=False
                )

            return result.inserted_id
        except Exception as e:
            logger.error(f"Failed to create OTA telemetry: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            return None

    @staticmethod
    async def get_telemetry_by_session(session_id: str):
        try:
            from bson import ObjectId
            session_ids = [session_id]
            try:
                session_ids.append(int(session_id))
            except (ValueError, TypeError):
                pass

            # Resolve update session document if exists to match both _id and session_id
            update_sess_doc = None
            if ObjectId.is_valid(session_id):
                update_sess_doc = await db.ota_update_sessions.find_one({"_id": ObjectId(session_id), "deleted_at": None})
            if not update_sess_doc:
                update_sess_doc = await db.ota_update_sessions.find_one({"session_id": session_id, "deleted_at": None})
            if not update_sess_doc:
                try:
                    update_sess_doc = await db.ota_update_sessions.find_one({"session_id": int(session_id), "deleted_at": None})
                except (ValueError, TypeError):
                    pass

            if update_sess_doc:
                raw_sess_id = update_sess_doc.get("session_id")
                raw_doc_id = str(update_sess_doc.get("_id"))
                if raw_sess_id is not None:
                    session_ids.append(str(raw_sess_id))
                    try:
                        session_ids.append(int(raw_sess_id))
                    except (ValueError, TypeError):
                        pass
                if raw_doc_id:
                    session_ids.append(raw_doc_id)

            session_ids = list(set(session_ids))

            query = {"session_id": {"$in": session_ids}, "deleted_at": None}
            cursor = db.ota_telemetries.find(query).sort("timestamp", 1)
            results = []
            seen_devices = set()
            async for doc in cursor:
                results.append(OtaTelemetryResponse(**doc))
                seen_devices.add(doc.get("device_id"))

            # Also check ota_session_acks for any additional records
            ack_query = {"update_session_id": {"$in": [str(s) for s in session_ids]}, "deleted_at": None}
            ack_cursor = db.ota_session_acks.find(ack_query)
            async for ack in ack_cursor:
                end_dev_id = ack.get("end_device_id", "")
                if end_dev_id not in seen_devices:
                    created_val = ack.get("acked_at") or ack.get("inserted_at")
                    results.append(OtaTelemetryResponse(
                        _id=ack["_id"],
                        session_id=str(ack.get("update_session_id")),
                        device_id=end_dev_id,
                        stage="completed" if ack.get("status") == "success" else (ack.get("status") or "pending"),
                        metrics={"notes": ack.get("notes")},
                        created_at=created_val.isoformat() if created_val else None
                    ))

            return results
        except Exception as e:
            logger.error(f"Failed to get OTA telemetry for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
