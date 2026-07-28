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
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.messaging.mqtt_client import start_mqtt_client
from app.routes import user_routes, role_routes, device_routes, project_routes, sensor_routes, token_routes, \
    widget_routes, server_routes, amedas_routes, tenki_routes, edge_routes, edge_data_routes, edge_ota_routes, end_device_routes, firmware_release_routes, rotation_request_routes, update_session_routes, dashboard_routes
from app.routes.k8s import kub_sensor_routes
from app.routes.firmware import firmware_routes
from app.scripts.amedas_scheduler import service_amedas_scheduler
from app.scripts.tenki_scheduler import service_tenki_scheduler
from app.utils.db import Database
from app.utils.driver_manager import close_shared_driver
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://fastapi.sinaungoding.com",
    "https://web.sinaungoding.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrumentor = Instrumentator().instrument(app).expose(app)

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

    # asyncio.create_task(service_amedas_scheduler())
    # the information about cedar pollen currently unavailable
    # asyncio.create_task(service_tenki_scheduler())


@app.on_event("shutdown")
async def shutdown():
    global running
    logger.info("Server shutting down...")
    running = False
    await close_shared_driver()


app.include_router(sensor_routes.router, prefix="/api/v1", tags=["Sensors"])
app.include_router(kub_sensor_routes.router, prefix="/api/v1", tags=["KubSensors"])
app.include_router(firmware_routes.router, prefix="/api/v1", tags=["Firmwares"])
app.include_router(token_routes.router, prefix="/api/v1", tags=["Tokens"])
app.include_router(device_routes.router, prefix="/api/v1", tags=["Devices"])
app.include_router(edge_routes.router, prefix="/api/v1", tags=["Edges"])
app.include_router(edge_ota_routes.router, prefix="/api/v1", tags=["EdgeOtas"])
app.include_router(end_device_routes.router, prefix="/api/v1", tags=["EndDevices"])
app.include_router(firmware_release_routes.router, prefix="/api/v1", tags=["FirmwareReleases"])
app.include_router(rotation_request_routes.router, prefix="/api/v1", tags=["RotationRequests"])
app.include_router(update_session_routes.router, prefix="/api/v1", tags=["UpdateSessions"])
app.include_router(dashboard_routes.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(edge_data_routes.router, prefix="/api/v1", tags=["EdgesData"])
app.include_router(project_routes.router, prefix="/api/v1", tags=["Projects"])
app.include_router(user_routes.router, prefix="/api/v1", tags=["Users"])
app.include_router(role_routes.router, prefix="/api/v1", tags=["Roles"])
app.include_router(widget_routes.router, prefix="/api/v1", tags=["Widgets"])
app.include_router(server_routes.router, prefix="/api/v1", tags=["Servers"])
app.include_router(amedas_routes.router, prefix="/api/v1", tags=["Amedas"])
app.include_router(tenki_routes.router, prefix="/api/v1", tags=["Tenki"])
app.include_router(route_unsecure)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
