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

            new_telemetry = OtaTelemetry(
                session_id=telemetry_data.session_id,
                device_id=telemetry_data.device_id,
                stage=telemetry_data.stage,
                metrics=telemetry_data.metrics,
                timestamp=ts,
                inserted_at=now_utc,
                inserted_by=user_id
            )

            result = await db.ota_telemetries.insert_one(new_telemetry.model_dump(by_alias=True))
            logger.info(f"[OTA_TELEMETRY] Inserted telemetry id={result.inserted_id} for device={telemetry_data.device_id}, stage={telemetry_data.stage}")

            # Intercept Key Rotation ACK stages
            if telemetry_data.stage in ("rotation_success", "rotation_ack", "rotation_completed"):
                from app.services.ota_rotation_request_service import RotationRequestService
                await RotationRequestService.add_rotation_ack(
                    rotation_id=telemetry_data.session_id,
                    device_id=telemetry_data.device_id,
                    success=True
                )
            elif telemetry_data.stage in ("rotation_failed", "rotation_error"):
                from app.services.ota_rotation_request_service import RotationRequestService
                await RotationRequestService.add_rotation_ack(
                    rotation_id=telemetry_data.session_id,
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
            query = {"session_id": session_id, "deleted_at": None}
            cursor = db.ota_telemetries.find(query).sort("timestamp", 1)
            results = []
            async for doc in cursor:
                results.append(OtaTelemetryResponse(**doc))
            return results
        except Exception as e:
            logger.error(f"Failed to get OTA telemetry for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
