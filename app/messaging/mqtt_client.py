# mqtt_client.py
import asyncio
import json
from datetime import datetime

import paho.mqtt.client as mqtt
import pytz

from app.schemas.sensor_actuator_schema import SensorActuatorCreate
from app.schemas.server_schema import ServerResponse
from app.schemas.token_schema import TokenDataDevice
from app.services.device_service import DeviceService
from app.services.sensor_actuator_service import SensorActuatorService
from app.services.server_service import ServerService
from app.utils.config import ACCESS_TOKEN_SECRET, ENV
from app.utils.encryption_tools import decrypt_cha_data
from app.utils.logger import get_logger

logger = get_logger(__name__)

mqtt_cli = None
topic_devices = []
running = True
topic_pub: str
topic_sub: str
topic_sub_device: str
topic_unsub_device: str
qos: int
server: ServerResponse


# Callback saat koneksi berhasil
async def on_connect_async(client, userdata, flags, rc):
    try:
        global running, topic_sub, topic_sub_device, topic_unsub_device, qos, topic_pub
        logger.info(f"Connected with result code {rc}")
        devices = await DeviceService.get_active_all_devices("mqtt")
        if not devices:
            logger.warning(".......................................")
            logger.warning(f"Not any device, please create first...")
            logger.warning(".......................................")

        topic_pub = server.parameters['topics']['publish']
        topic_sub = server.parameters['topics']['subscribe']
        logger.info(f"topic_pub: {topic_pub}")
        topic_sub_device = server.parameters['topics']['subscribe_device']
        topic_unsub_device = server.parameters['topics']['unsubscribe_device']
        qos = server.parameters['qos']
        for device in devices:
            topic_devices.append((topic_sub + device.code))
            logger.info(f"device: {device}")
            logger.info(f"topic: {(topic_sub + device.code)}")
            client.subscribe(topic_sub + device.code, qos=qos)
        client.subscribe(topic_sub_device, qos=qos)
        client.subscribe(topic_unsub_device, qos=qos)
    except Exception as e:
        logger.error(f"Error on_connect: {e}")


# Synchronous wrapper for on_connect
def on_connect(client, userdata, flags, rc):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(on_connect_async(client, userdata, flags, rc), loop)


# Callback saat pesan diterima
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        logger.info(f"Message received: {payload} topic: {msg.topic}")
        if msg.topic in topic_devices:
            data = json.loads(payload)
            token_dev = data.get("token")
            try:
                json_token = decrypt_cha_data(ACCESS_TOKEN_SECRET, token_dev)
                logger.info(f"Token: {json_token}")
                dt = SensorActuatorCreate(
                    device_id=json_token['dev_id'],
                    device_code=json_token['dev_code'],
                    data=data.get("data"),
                    timestamp=datetime.now(tz=pytz.UTC))
                token_dev = TokenDataDevice(
                    user_id=json_token['usr_id'],
                    device_id=dt.device_id,
                    device_code=dt.device_code
                )
                asyncio.create_task(process_sensor_data(client, dt, token_dev))
            except Exception as e:
                logger.warning(f"Warning on_message: {e}")
        elif msg.topic == topic_sub_device:
            device_code = payload
            client.subscribe(topic_sub + device_code, qos=1)
            logger.info(f"topic sub devices      : {topic_devices}")
            topic_devices.append(topic_sub + device_code)
            logger.info(f"topic sub devices after: {topic_devices}")
        elif msg.topic == topic_unsub_device:
            device_code = payload
            client.unsubscribe(topic_sub + device_code)
            logger.info(f"topic unsub devices      : {topic_devices}")
            topic_devices.remove(topic_sub + device_code)
            logger.info(f"topic unsub devices after: {topic_devices}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except Exception as e:
        logger.error(f"Error on_message: {e}")


async def process_sensor_data(client, data: SensorActuatorCreate, token: TokenDataDevice):
    try:
        res = await SensorActuatorService.create_sensor_data(data, token)
        res.id = str(res.id)
        logger.info(f"res: {res} {type(res)}")
        payload = vars(res)
        logger.info(f"payload: {payload}")
        client.publish(topic=(topic_pub + token.device_code), payload=json.dumps(payload), qos=1)
    except Exception as e:
        logger.error(f"Error on_message: {e}")


# Fungsi untuk memulai MQTT client
async def start_mqtt_client():
    global mqtt_cli, server, running
    try:
        server = await ServerService.get_server_config(protocol="mqtt", environment=ENV)
        if not server:
            logger.error(".......................................")
            logger.error(f"Not any server configuration, please create first...")
            logger.error(".......................................")
            running = False
        logger.info(f"server: {server}")

        logger.info("Starting MQTT client")
        mqtt_cli = mqtt.Client()
        mqtt_cli.username_pw_set(server.parameters['username'], server.parameters['password'])
        mqtt_cli.on_connect = on_connect
        mqtt_cli.on_message = on_message
        logger.info(f"connecting MQTT broker: {server.host} port: {server.ports['mqtt']}")
        mqtt_cli.connect(server.host, server.ports['mqtt'], server.parameters['keep_alive'])
        while running:
            mqtt_cli.loop(timeout=1)
            await asyncio.sleep(1)
        mqtt_cli.disconnect()
        logger.info("Disconnected")
    except Exception as e:
        logger.error(f"Error in start_mqtt_client: {e}")
