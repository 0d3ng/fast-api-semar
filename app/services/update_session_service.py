import traceback
from datetime import datetime

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.models.session_ack import SessionAck
from app.models.update_session import UpdateSession
from app.schemas.session_ack_schema import SessionAckCreate, SessionAckResponse
from app.schemas.token_schema import TokenData
from app.schemas.update_session_schema import UpdateSessionCreate, UpdateSessionResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UpdateSessionService:
    @staticmethod
    async def create_session(session_data: UpdateSessionCreate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            new_session: UpdateSession = UpdateSession(
                session_id=session_data.session_id,
                type=session_data.type,
                firmware_release_id=session_data.firmware_release_id,
                rotation_request_id=session_data.rotation_request_id,
                target_edge_ota_id=session_data.target_edge_ota_id,
                status=session_data.status or "preparing",
                started_at=now_utc,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.update_sessions.insert_one(new_session.model_dump(by_alias=True))
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
            doc = await db.update_sessions.find_one({"_id": ObjectId(session_id), "deleted_at": None})
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
            cursor = db.update_sessions.find({"deleted_at": None})
            async for doc in cursor:
                sessions.append(UpdateSessionResponse(**doc))
            return sessions
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def add_session_ack(session_id: str, ack_data: SessionAckCreate, user_id: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            session = await db.update_sessions.find_one({"_id": ObjectId(session_id), "deleted_at": None})
            if not session:
                raise HTTPException(status_code=404, detail="UpdateSession not found")

            new_ack: SessionAck = SessionAck(
                update_session_id=session_id,
                end_device_id=ack_data.end_device_id,
                acked_at=now_utc,
                status=ack_data.status,
                notes=ack_data.notes,
                inserted_at=now_utc,
                inserted_by=user_id
            )
            inserted = await db.session_acks.insert_one(new_ack.model_dump(by_alias=True))
            new_id = inserted.inserted_id

            if new_id:
                # Update EndDevice last_update_at if status success
                if ack_data.status == "success":
                    await db.end_devices.update_one(
                        {"_id": ObjectId(ack_data.end_device_id)},
                        {"$set": {"last_update_at": now_utc}}
                    )

                return SessionAckResponse(
                    _id=new_id,
                    update_session_id=session_id,
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
