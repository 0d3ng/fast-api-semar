#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-06-12 05:22:07
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-06-12 05:22:07
#  File: kub_sensor_routes.py
#  Description:
#  """
from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.middlewares.auth import verify_keycloak_token
from app.schemas.sensor_actuator_schema import SensorActuatorResponse, SensorActuatorCreate
from app.services.sensor_actuator_service import SensorActuatorService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/kub_sensors", response_model=SensorActuatorResponse)
async def create_sensor(sensor_data: SensorActuatorCreate,
                        payload:dict = Depends(verify_keycloak_token)):
    try:
        return await SensorActuatorService.create_sensor_data_without_token(sensor_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
