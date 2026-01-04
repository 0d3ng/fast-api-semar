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
import zipfile
from fastapi import Request

from fastapi import APIRouter, UploadFile, File
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, JSONResponse

from app.messaging.mqtt_publisher import publish_message
from app.services.server_service import ServerService
from app.utils.logger import get_logger
from app.utils.config import FIRMWARE_FOLDER, FIRMWARE_UPDATE_TOPIC, ENV, MESSAGE_BROKER

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
        # make sure folder exists
        os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
        file_path = os.path.join(FIRMWARE_FOLDER, file.filename)
        # save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"Uploaded {file.filename}")
        # extract if zip file
        if file.filename.endswith(".zip"):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(FIRMWARE_FOLDER)
                logger.info(f"Extracted {file.filename} to {FIRMWARE_FOLDER}")
            except zipfile.BadZipFile:
                logger.error(f"Failed to extract {file.filename}: Not a zip file")
                raise HTTPException(status_code=400, detail="Invalid zip file")
        # Notify devices about firmware update
        server = await ServerService.get_server_config(protocol=MESSAGE_BROKER.lower(), environment=ENV)
        if server:
            qos = server.parameters['qos']
            publish_message(topic=FIRMWARE_UPDATE_TOPIC, payload="start", qos=qos, server=server)
        else:
            logger.warning("Server configuration not found")
        return JSONResponse(content={"message": f"File {file.filename} uploaded successfully"})
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")
