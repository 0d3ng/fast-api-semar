#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-09-24 16:32:35
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-09-24 16:32:35
#   File: firmware_routes.py
#   Description:
#   """
import os

from fastapi import APIRouter
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse

from app.utils.logger import get_logger
from app.utils.config import FIRMWARE_FOLDER

logger = get_logger(__name__)

router = APIRouter()


@router.get("/firmware/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(FIRMWARE_FOLDER, filename)
    logger.info(f"Downloading {filename}")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/octet-stream', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")
