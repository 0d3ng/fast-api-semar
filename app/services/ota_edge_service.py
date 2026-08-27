from typing import Optional
import time
import traceback
from datetime import datetime

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.messaging.mqtt_publisher import publish_message
from app.middlewares.auth import create_token_enc, create_access_token
from app.models.ota_edge import EdgeOta
from app.models.token import Token
from app.schemas.ota_edge_schema import EdgeOtaCreateUpdate, EdgeOtaResponse
from app.schemas.token_schema import TokenData
from app.services.server_service import ServerService
from app.utils.config import ACCESS_TOKEN_EXPIRE_DEVICE_DAYS
from app.utils.db import db
from app.utils.generator import generate_random_alphanumeric_hexa, add_day_to_date
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdgeOtaService:
    @staticmethod
    async def create_edge_ota(edge_ota: EdgeOtaCreateUpdate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            logger.info(edge_ota)
            new_edge_ota: EdgeOta = EdgeOta(
                code=generate_random_alphanumeric_hexa(),
                name=edge_ota.name,
                ip_address=edge_ota.ip_address,
                multicast_group=edge_ota.multicast_group,
                multicast_port=edge_ota.multicast_port,
                ttl=edge_ota.ttl,
                chunk_size=edge_ota.chunk_size,
                description=edge_ota.description,
                status="offline",
                project_id=edge_ota.project_id,
                active=edge_ota.active,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            logger.info(new_edge_ota)
            inserted = await db.ota_edges.insert_one(new_edge_ota.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            logger.info(f"{new_id} {type(new_id)}")
            if new_id:
                future = add_day_to_date(days=int(ACCESS_TOKEN_EXPIRE_DEVICE_DAYS))
                payload = {
                    "usr_id": current_user.user_id,
                    "dev_id": str(new_id),
                    "dev_code": new_edge_ota.code,
                    "exp": int(time.mktime(future.timetuple()))
                }
                protocol = getattr(edge_ota, "protocol", None)
                if protocol == "mqtt":
                    access_token = create_token_enc(payload=payload)
                    server = await ServerService.get_server_config(protocol, environment="development")
                    if server:
                        topic = server.parameters['topics']['subscribe_device']
                        qos = server.parameters['qos']
                        publish_message(topic=topic, payload=new_edge_ota.code, qos=qos, server=server)
                    else:
                        logger.warning("Server configuration not found")
                else:
                    payload = {
                        "usr_id": current_user.user_id,
                        "username": current_user.username,
                        "dev_id": str(new_id),
                        "dev_code": new_edge_ota.code
                    }
                    access_token = create_access_token(data=payload)
                new_token: Token = Token(
                    device_id=str(new_id),
                    name=new_edge_ota.name,
                    token=access_token,
                    description=new_edge_ota.description,
                    expires_at=future,
                    inserted_at=now_utc,
                    inserted_by=current_user.user_id
                )
                logger.info(new_token)
                new_token_inserted = await db.tokens.insert_one(new_token.model_dump(by_alias=True))
                new_token_id = new_token_inserted.inserted_id
                if new_token_id:
                    logger.info(f"{new_token_id} {type(new_token_id)} created successfully")
                    return EdgeOtaResponse(
                        _id=new_id,
                        code=new_edge_ota.code,
                        name=new_edge_ota.name,
                        ip_address=new_edge_ota.ip_address,
                        multicast_group=new_edge_ota.multicast_group,
                        multicast_port=new_edge_ota.multicast_port,
                        ttl=new_edge_ota.ttl,
                        chunk_size=new_edge_ota.chunk_size,
                        description=new_edge_ota.description,
                        status=new_edge_ota.status,
                        project_id=new_edge_ota.project_id,
                        active=new_edge_ota.active,
                        inserted_at=now_utc,
                        inserted_by=current_user.user_id
                    )
                else:
                    raise HTTPException(status_code=500, detail="Create token fail")
            raise HTTPException(status_code=500, detail="Insert edge_ota failed")
        except Exception as e:
            logger.error(f"Failed to create edge_ota: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_edge_ota(edge_ota_id: str):
        try:
            query = {"deleted_at": None}
            if ObjectId.is_valid(edge_ota_id):
                query["$or"] = [{"_id": ObjectId(edge_ota_id)}, {"code": edge_ota_id}]
            else:
                query["code"] = edge_ota_id
            doc = await db.ota_edges.find_one(query)
            if doc:
                return EdgeOtaResponse(**doc)
            raise HTTPException(status_code=404, detail="EdgeOta not found")
        except HTTPException:
            raise
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_edge_otas(user_id: str = None, active: Optional[bool] = None):
        try:
            edges = []
            filter_query = {"deleted_at": None}
            if user_id:
                filter_query["inserted_by"] = user_id
            if active is not None:
                filter_query["active"] = active
            cursor = db.ota_edges.find(filter_query)
            async for doc in cursor:
                edges.append(EdgeOtaResponse(**doc))
            return edges
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_edge_ota(edge_ota_id: str, edge_ota_update: EdgeOtaCreateUpdate, current_user: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            update_data = {k: v for k, v in edge_ota_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = now_utc
            update_data["updated_by"] = current_user
            result = await db.ota_edges.update_one({"_id": ObjectId(edge_ota_id), "deleted_at": None}, {"$set": update_data})
            if result.matched_count == 1:
                return await EdgeOtaService.get_edge_ota(edge_ota_id)
            return None
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_edge_ota(edge_ota_id: str, current_user: str):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            update_data = {
                "deleted_at": now_utc,
                "deleted_by": current_user
            }
            result = await db.ota_edges.update_one({"_id": ObjectId(edge_ota_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
