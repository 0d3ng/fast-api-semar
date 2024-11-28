import os
from datetime import datetime, timedelta

import jwt
from bson import ObjectId
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user_schema import Token
from app.schemas.user_schema import UserCreate, UserUpdate
from app.utils.db import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    async def authenticate_user(email: str, password: str):
        user = await db.users.find_one({"email": email})
        if user and pwd_context.verify(password, user['hashed_password']):
            return User(**user)
        return None

    @staticmethod
    async def create_access_token(user: User):
        from pytz import timezone
        expire = datetime.now(tz=timezone("Asia/Tokyo")) + timedelta(minutes=int(os.getenv("JWT_EXPIRE_HOURS")))
        payload = {
            "user_id": str(user.id),
            "exp": expire,
        }
        token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm=os.getenv("JWT_ALGORITHM"))
        return Token(access_token=token, token_type="bearer")

    @staticmethod
    async def create_user(user: UserCreate, current_user: str):
        hashed_password = pwd_context.hash(user.password)
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            inserted_at=datetime.utcnow().isoformat(),
            updated_by=current_user
        )
        await db.users.insert_one(new_user.dict(by_alias=True))
        return new_user

    @staticmethod
    async def get_user(user_id: str):
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            return User(**user)
        return None

    @staticmethod
    async def get_all_users():
        users = []
        cursor = db.users.find({})
        async for user in cursor:
            users.append(User(**user))
        return users

    @staticmethod
    async def update_user(user_id: str, user_update: UserUpdate, current_user: str):
        update_data = {k: v for k, v in user_update.dict(exclude_unset=True).items() if v is not None}
        if "password" in update_data:
            update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
        update_data["updated_at"] = datetime.utcnow().isoformat()
        update_data["updated_by"] = current_user
        result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        if result.matched_count == 1:
            return await UserService.get_user(user_id)
        return None

    @staticmethod
    async def delete_user(user_id: str, current_user: str):
        update_data = {
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": current_user
        }
        result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        if result.matched_count == 1:
            return True
        return False
