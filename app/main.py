#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:47:38
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 21:05:08
#  File: main.py
#  Description:
#  """
import asyncio
import os
import signal

import fastapi
import uvicorn
from fastapi import FastAPI, APIRouter
from starlette.responses import JSONResponse

from app.messaging.mqtt_client import start_mqtt_client, mqtt_cli
from app.routes import user_routes, role_routes, device_routes, project_routes, sensor_routes, token_routes
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()

route_unsecure = APIRouter(prefix="/api/v1", tags=["Unsecure"])


@route_unsecure.get("/shutdown")
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return fastapi.Response(status_code=200, content='Server shutting down...')


@route_unsecure.get("/health")
def ping():
    return JSONResponse(status_code=200, content={"message": "pong"})


@app.on_event("startup")
async def startup():
    logger.info("Server starting up...")
    asyncio.create_task(start_mqtt_client())


@app.on_event("shutdown")
async def shutdown():
    logger.info("Server shutting down...")
    mqtt_cli.loop_stop()
    mqtt_cli.disconnect()


app.include_router(sensor_routes.router, prefix="/api/v1", tags=["Sensors"])
app.include_router(token_routes.router, prefix="/api/v1", tags=["Tokens"])
app.include_router(device_routes.router, prefix="/api/v1", tags=["Devices"])
app.include_router(project_routes.router, prefix="/api/v1", tags=["Projects"])
app.include_router(user_routes.router, prefix="/api/v1", tags=["Users"])
app.include_router(role_routes.router, prefix="/api/v1", tags=["Roles"])
app.include_router(route_unsecure)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
