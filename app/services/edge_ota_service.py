import traceback
from datetime import datetime

import pytz
from bson import ObjectId
from fastapi import HTTPException

from app.models.edge_ota import EdgeOta
from app.schemas.edge_ota_schema import EdgeOtaCreateUpdate, EdgeOtaResponse
from app.schemas.token_schema import TokenData
from app.utils.db import db
from app.utils.generator import generate_random_alphanumeric_hexa
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdgeOtaService:
    @staticmethod
    async def create_edge_ota(edge_ota: EdgeOtaCreateUpdate, current_user: TokenData):
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            new_edge_ota: EdgeOta = EdgeOta(
                code=generate_random_alphanumeric_hexa(),
                name=edge_ota.name,
                ip_address=edge_ota.ip_address,
                multicast_group=edge_ota.multicast_group,
                multicast_port=edge_ota.multicast_port,
                description=edge_ota.description,
                status="offline",
                project_id=edge_ota.project_id,
                active=edge_ota.active,
                inserted_at=now_utc,
                inserted_by=current_user.user_id
            )
            inserted = await db.edge_otas.insert_one(new_edge_ota.model_dump(by_alias=True))
            new_id = inserted.inserted_id
            if new_id:
                return EdgeOtaResponse(
                    _id=new_id,
                    code=new_edge_ota.code,
                    name=new_edge_ota.name,
                    ip_address=new_edge_ota.ip_address,
                    multicast_group=new_edge_ota.multicast_group,
                    multicast_port=new_edge_ota.multicast_port,
                    description=new_edge_ota.description,
                    status=new_edge_ota.status,
                    project_id=new_edge_ota.project_id,
                    active=new_edge_ota.active,
                    inserted_at=now_utc,
                    inserted_by=current_user.user_id
                )
            raise HTTPException(status_code=500, detail="Insert edge_ota failed")
        except Exception as e:
            logger.error(f"Failed to create edge_ota: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_edge_ota(edge_ota_id: str):
        try:
            doc = await db.edge_otas.find_one({"_id": ObjectId(edge_ota_id), "deleted_at": None})
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
    async def get_all_edge_otas(user_id: str = None):
        try:
            edges = []
            filter_query = {"deleted_at": None}
            if user_id:
                filter_query["inserted_by"] = user_id
            cursor = db.edge_otas.find(filter_query)
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
            result = await db.edge_otas.update_one({"_id": ObjectId(edge_ota_id), "deleted_at": None}, {"$set": update_data})
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
            result = await db.edge_otas.update_one({"_id": ObjectId(edge_ota_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
