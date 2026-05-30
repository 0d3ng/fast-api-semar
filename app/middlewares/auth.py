#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:45:51
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 21:05:08
#  File: auth.py
#  Description:
#  """

import traceback
from datetime import datetime, timedelta
from functools import lru_cache

import httpx
import pytz
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette import status

bearer_scheme = HTTPBearer()

from app.schemas.token_schema import TokenData, TokenDataDevice
from app.utils.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET, ACCESS_TOKEN_SECRET, JWKS_URL
from app.utils.encryption_tools import decrypt_cha_data, encrypt_cha_data
from app.utils.logger import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(pytz.UTC) + expires_delta
    else:
        expire = datetime.now(pytz.UTC) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    logger.info(to_encode)
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception, is_device: bool = False):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if is_device:
            user_id: str = payload.get("usr_id")
            device_id: str = payload.get("dev_id")
            device_code: str = payload.get("dev_code")
            if device_id is None:
                raise credentials_exception
            token_data = TokenDataDevice(user_id=user_id, device_id=device_id, device_code=device_code)
        else:
            user_id: str = payload.get("user_id")
            username: str = payload.get("username")
            if username is None:
                raise credentials_exception
            token_data = TokenData(user_id=user_id, username=username)

    except (JWTError, Exception) as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise credentials_exception
    return token_data


def verify_token_device(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("usr_id")
        device_id: str = payload.get("dev_id")
        device_code: str = payload.get("dev_code")
        if device_id is None:
            raise Exception("device_id is None")
        token_data = TokenDataDevice(user_id=user_id, device_id=device_id, device_code=device_code)
    except (JWTError, Exception) as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise Exception
    return token_data


def create_token_enc(payload):
    try:
        token = encrypt_cha_data(ACCESS_TOKEN_SECRET, payload)
        return token
    except Exception as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise Exception


def verify_token_enc(token: str):
    try:
        payload = decrypt_cha_data(ACCESS_TOKEN_SECRET, token)
        user_id: str = payload["usr_id"]
        device_id: str = payload["dev_id"]
        device_code: str = payload["dev_code"]
        exp: str = payload["exp"]
        if device_id is None or user_id is None or device_code is None or exp is None:
            raise Exception("Token is wrong")
        exp_date = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
        if exp_date < datetime.now(pytz.UTC):
            raise Exception("Token is expired")
        token_data = TokenDataDevice(user_id=user_id, device_id=device_id, device_code=device_code)
    except (JWTError, Exception) as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise Exception
    return token_data

@lru_cache(maxsize=1)
def get_keycloak_jwks() -> dict:
    """Fetch public key dari Keycloak sekali saja — verifikasi JWT offline."""
    response = httpx.get(JWKS_URL, timeout=10)
    response.raise_for_status()
    return response.json()

def verify_keycloak_token(credentials = Depends(bearer_scheme)) -> dict:
    """Dependency untuk endpoint yang diprotect Keycloak."""
    try:
        jwks = get_keycloak_jwks()
        payload = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        logger.error(f"Keycloak token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Keycloak tidak valid",
            headers={"WWW-Authenticate": "Bearer"},
        )