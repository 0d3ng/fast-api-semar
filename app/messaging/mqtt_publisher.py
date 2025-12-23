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
import ssl

import certifi
import paho.mqtt.client as mqtt

from app.schemas.server_schema import ServerResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


def publish_message(topic, payload, server: ServerResponse, qos=1):
    client = mqtt.Client()
    try:
        client.username_pw_set(server.parameters['username'], server.parameters['password'])
        logger.info(f"Protocol: {server.protocol} Host: {server.host} Port: {server.ports['mqtt']}")
        if server.protocol == 'mqtts':
            client.tls_set(ca_certs=certifi.where(), tls_version=ssl.PROTOCOL_TLS)
        client.connect(server.host, server.ports['mqtt'], server.parameters['keep_alive'])
        client.loop_start()
        logger.info(f"publish data: {payload} with topic: {topic}")
        result = client.publish(topic, payload, qos=qos)
        result.wait_for_publish()
        logger.info(f"publish successful!")
    except Exception as e:
        logger.error(e)
    finally:
        client.loop_stop()
        if client.is_connected():
            client.disconnect()
