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

from app.utils.config import MQTT_USERNAME, MQTT_PASSWORD, MQTT_BROKER, MQTT_PORT
from app.utils.logger import get_logger

logger = get_logger(__name__)


def publish_message(topic, payload, qos=1):
    client = mqtt.Client()
    try:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        logger.info(f"publish data: {payload} with topic: {topic}")
        client.publish(topic, payload, qos=qos)
    except Exception as e:
        logger.error(e)
    finally:
        if client.is_connected():
            client.disconnect()
