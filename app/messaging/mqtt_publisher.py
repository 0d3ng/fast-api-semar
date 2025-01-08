#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-24 18:53:23
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-24 18:53:23
#   File: mqtt_publisher.py
#   Description:
#   """
import paho.mqtt.client as mqtt

from app.schemas.server_schema import ServerResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


def publish_message(topic, payload, server: ServerResponse, qos=1):
    client = mqtt.Client()
    try:
        client.username_pw_set(server.parameters['username'], server.parameters['password'])
        client.connect(server.host, server.ports['mqtt'], server.parameters['keep_alive'])
        logger.info(f"publish data: {payload} with topic: {topic}")
        client.publish(topic, payload, qos=qos)
    except Exception as e:
        logger.error(e)
    finally:
        if client.is_connected():
            client.disconnect()
