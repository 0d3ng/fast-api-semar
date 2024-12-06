import os
import traceback
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.middlewares.auth import create_access_token
from app.models.token import Token
from app.models.user import User
from app.schemas.token_schema import TokenCreate, TokenResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class TokenService:
    @staticmethod
    async def create_token(token: TokenCreate, user: User):
        try:
            logger.info(token)
            expire = timedelta(minutes=int(token.expires_in))
            payload = {
                "user_id": user.id,
                "username": user.username
            }
            access_token = create_access_token(payload, expires_delta=expire)
            new_token: Token = Token(
                user_id=token.user_id,
                name=token.name,
                token=access_token,
                description=token.description,
                expires_at=token.expires_at,
                inserted_at=datetime_jpn,
                inserted_by=user.id
            )
            logger.info(new_token)
            new_token_inserted = await db.tokens.insert_one(new_token.model_dump(by_alias=True))
            new_token_id = new_token_inserted.inserted_id
            return TokenResponse(_id=new_token_id,
                                 user_id=token.user_id,
                                 name=token.name,
                                 token=access_token,
                                 description=token.description,
                                 expires_at=token.expires_at,
                                 inserted_at=datetime_jpn,
                                 inserted_by=user.id
                                 )
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_token(token_id: str):
        try:
            token = await db.users.find_one({"_id": ObjectId(token_id)})
            if token:
                return TokenResponse(**token)
            raise HTTPException(status_code=404, detail="Token not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_tokens():
        try:
            tokens = []
            cursor = db.tokenss.find({})
            async for token in cursor:
                logger.info(f"{token} {token["_id"]}")
                token_response = TokenResponse(**token)
                tokens.append(token_response)
                logger.info("")
            return tokens
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_token(token_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.tokens.update_one({"_id": ObjectId(token_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
