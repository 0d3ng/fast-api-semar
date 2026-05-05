import time
import traceback
from datetime import datetime

import pytz
from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext

from app.messaging.mqtt_publisher import publish_message
from app.middlewares.auth import create_token_enc, create_access_token
from app.models.device import Device
from app.models.edge import Edge
from app.models.token import Token
from app.schemas.device_schema import DeviceCreateUpdate, DeviceResponse
from app.schemas.edge_schema import EdgeCreateUpdate, EdgeResponse
from app.schemas.token_schema import TokenData
from app.services.server_service import ServerService
from app.utils.config import ACCESS_TOKEN_EXPIRE_DEVICE_DAYS
from app.utils.db import db
from app.utils.generator import generate_random_alphanumeric_hexa, add_day_to_date
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class EdgeService:
    @staticmethod
    async def create_edge(edge: EdgeCreateUpdate, current_user: TokenData):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            logger.info(edge)
            new_edge: Edge = Edge(
                code=generate_random_alphanumeric_hexa(),
                name=edge.name,
                description=edge.description,
                type=edge.type,
                protocol=edge.protocol,
                project_id=edge.project_id,
                active=edge.active,
                config=edge.config,
                inserted_at=datetime_jpn,
                inserted_by=current_user.user_id
            )
            logger.info(new_edge)
            new_edge_inserted = await db.edges.insert_one(new_edge.model_dump(by_alias=True))
            new_edge_id = new_edge_inserted.inserted_id
            logger.info(f"{new_edge_id} {type(new_edge_id)}")
            if new_edge_id:
                future = add_day_to_date(days=int(ACCESS_TOKEN_EXPIRE_DEVICE_DAYS))
                payload = {
                    "usr_id": current_user.user_id,
                    "dev_id": str(new_edge_id),
                    "dev_code": new_edge.code,
                    "exp": int(time.mktime(future.timetuple()))
                }
                if edge.protocol == "mqtt":
                    access_token = create_token_enc(payload=payload)
                    server = await ServerService.get_server_config(new_edge.protocol, environment="development")
                    if server:
                        topic = server.parameters['topics']['subscribe_device']
                        qos = server.parameters['qos']
                        publish_message(topic=topic, payload=new_edge.code, qos=qos, server=server)
                    else:
                        logger.warning("Server configuration not found")
                else:
                    payload = {
                        "usr_id": current_user.user_id,
                        "username": current_user.username,
                        "dev_id": str(new_edge_id),
                        "dev_code": new_edge.code
                    }
                    access_token = create_access_token(data=payload)
                new_token: Token = Token(
                    device_id=str(new_edge_id),
                    name=new_edge.name,
                    token=access_token,
                    description=new_edge.description,
                    expires_at=future,
                    inserted_at=datetime_jpn,
                    inserted_by=current_user.user_id
                )
                logger.info(new_token)
                new_token_inserted = await db.tokens.insert_one(new_token.model_dump(by_alias=True))
                new_token_id = new_token_inserted.inserted_id
                if new_token_id:
                    logger.info(f"{new_token_id} {type(new_token_id)} created successfully")
                    return EdgeResponse(_id=new_edge_id,
                                        code=new_edge.code,
                                        name=edge.name,
                                        description=edge.description,
                                        type=edge.type,
                                        protocol=edge.protocol,
                                        project_id=edge.project_id,
                                        active=edge.active,
                                        config=edge.config,
                                        inserted_at=datetime_jpn,
                                        inserted_by=current_user.user_id)
                else:
                    raise HTTPException(status_code=500, detail="Create token fail")
            raise HTTPException(status_code=500, detail="Insert edge fail")
        except Exception as e:
            logger.error(f"Failed to create edge: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_edge(edge_id: str):
        try:
            project = await db.edges.find_one({"_id": ObjectId(edge_id)})
            if project:
                return EdgeResponse(**project)
            raise HTTPException(status_code=404, detail="Edge not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_edges(user_id: str = None):
        try:
            projects = []
            if user_id:
                filter = {"inserted_by": user_id}
            else:
                filter = {}
            cursor = db.edges.find(filter)
            async for project in cursor:
                logger.info(f"{project} {project["_id"]}")
                project_response = EdgeResponse(**project)
                projects.append(project_response)
                logger.info("")
            return projects
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_active_all_edges(protocol):
        try:
            edges = []
            cursor = db.edges.find({
                "active": True,
                "deleted_at": {"$eq": None},
                "protocol": {"$eq": protocol}
            })
            async for edge in cursor:
                logger.info(f"{edge} {edge["_id"]}")

                project_response = EdgeResponse(**edge)
                edges.append(project_response)
                logger.info("")
            return edges
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_edge(edge_id: str, edge_update: EdgeCreateUpdate, current_user: str):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            update_data = {k: v for k, v in edge_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            result = await db.edges.update_one({"_id": ObjectId(edge_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await EdgeService.get_edge(edge_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_edge(edge_id: str, current_user: str):
        try:
            datetime_jpn = datetime.now(tz=pytz.UTC)
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.edges.update_one({"_id": ObjectId(edge_id)}, {"$set": update_data})
            if result.matched_count == 1:
                edge = await db.edges.find_one({"_id": ObjectId(edge_id)})
                if edge:
                    server = await ServerService.get_server_config(edge["protocol"], environment="development")
                    if server:
                        if server.protocol != "http":
                            topic = server.parameters['topics']['unsubscribe_device']
                            qos = server.parameters['qos']
                            publish_message(topic=topic, payload=edge["code"], qos=qos, server=server)
                            return True
                        return True
                    raise HTTPException(status_code=404, detail="Server configuration not found")
                raise HTTPException(status_code=404, detail="Edge not found")
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
