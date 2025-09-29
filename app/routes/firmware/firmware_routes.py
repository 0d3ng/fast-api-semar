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
from fastapi import Request

from fastapi import APIRouter, UploadFile, File
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, JSONResponse

from app.utils.logger import get_logger
from app.utils.config import FIRMWARE_FOLDER

logger = get_logger(__name__)

router = APIRouter()


@router.get("/firmware/{filename}")
async def download_file(filename: str, request: Request):
    logger.info(f"Incoming request headers: {request.headers}")
    file_path = os.path.join(FIRMWARE_FOLDER, filename)
    logger.info(f"Downloading {filename}")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/octet-stream', filename=filename,
                            headers={"Content-Disposition": f"attachment; filename={filename}"})
    raise HTTPException(status_code=404, detail="File not found")


@router.post("/firmware/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # pastikan folder ada
        os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
        file_path = os.path.join(FIRMWARE_FOLDER, file.filename)
        # simpan file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"Uploaded {file.filename}")
        return JSONResponse(content={"message": f"File {file.filename} uploaded successfully"})
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")
