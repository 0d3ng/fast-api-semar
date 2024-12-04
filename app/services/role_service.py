import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.models.role import Role
from app.schemas.role_schema import RoleCreateUpdate, RoleResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class RoleService:
    @staticmethod
    async def create_role(role: RoleCreateUpdate, current_user: str):
        try:
            logger.info(role)
            new_role: Role = Role(
                name=role.name,
                description=role.description,
                inserted_at=datetime_jpn,
                inserted_by=current_user
            )
            logger.info(new_role)
            new_role_inserted = await db.roles.insert_one(new_role.model_dump(by_alias=True))
            new_user_id = new_role_inserted.inserted_id
            return RoleResponse(_id=new_user_id,
                                name=role.name,
                                description=role.description,
                                inserted_at=datetime_jpn,
                                inserted_by=current_user)
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_role(role_id: str):
        try:
            role = await db.roles.find_one({"_id": ObjectId(role_id)})
            if role:
                return RoleResponse(**role)
            raise HTTPException(status_code=404, detail="Role not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_roles():
        try:
            roles = []
            cursor = db.roles.find({})
            async for role in cursor:
                logger.info(f"{role} {role["_id"]}")
                role_response = RoleResponse(**role)
                roles.append(role_response)
                logger.info("")
            return roles
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_role(role_id: str, role_update: RoleCreateUpdate, current_user: str):
        try:
            update_data = {k: v for k, v in role_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            result = await db.roles.update_one({"_id": ObjectId(role_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await RoleService.get_role(role_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_role(role_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.roles.update_one({"_id": ObjectId(role_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
