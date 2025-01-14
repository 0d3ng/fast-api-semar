from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.params import Query
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.sensor_actuator_schema import SensorActuatorResponse, SensorActuatorCreate, DataSource
from app.services.sensor_actuator_service import SensorActuatorService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/sensors/", response_model=SensorActuatorResponse)
async def create_sensor(sensor_data: SensorActuatorCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception, is_device=True)
        return await SensorActuatorService.create_sensor_data(sensor_data, token_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/sensors/{device_code}/sensor/{sensor_data_id}", response_model=SensorActuatorResponse)
async def read_sensor(sensor_data_id: str, device_code: str, token: str = Depends(oauth2_scheme)):
    try:
        logger.info(f"get sensor data by id: {sensor_data_id}")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await SensorActuatorService.get_sensor_data(sensor_data_id, device_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sensors/{device_code}/latest", response_model=SensorActuatorResponse)
async def read_last_sensor(device_code: str, token: str = Depends(oauth2_scheme)):
    try:
        logger.info(f"get last sensor data from {device_code}")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        response = await SensorActuatorService.get_last_sensor_data(device_code)
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sensors/{device_code}", response_model=List[SensorActuatorResponse])
async def read_sensors(device_code: str, token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get sensor data by code")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await SensorActuatorService.get_all_sensor_datas(device_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/sensors/", response_model=List[DataSource])
async def read_data_source(device_code: str = Query(...), start: str = Query(...), end: str = Query(...),
                           token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get datasource")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await SensorActuatorService.get_data_sources(device_code, start, end)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/sensors/{sensor_data_id}", response_model=SensorActuatorResponse)
async def update_sensor(sensor_data_id: str, sensor_data: SensorActuatorCreate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await SensorActuatorService.update_sensor_data(sensor_data_id, sensor_data, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return updated_user


@router.delete("/sensors/{sensor_data_id}/{device_code}")
async def delete_sensor(sensor_data_id: str, device_code: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await SensorActuatorService.delete_sensor_data(sensor_data_id, device_code, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"msg": "Sensor data deleted successfully"}
