# mqtt_client.py
import asyncio
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import pytz

from app.middlewares.auth import verify_token_device
from app.schemas.sensor_actuator_schema import SensorActuatorCreate
from app.schemas.token_schema import TokenDataDevice
from app.services.device_service import DeviceService
from app.services.sensor_actuator_service import SensorActuatorService
from app.utils.config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_TOPIC_RESPONSE, MQTT_USERNAME, MQTT_PASSWORD, \
    MQTT_TOPIC_DEVICE_UNSUB, MQTT_TOPIC_DEVICE_SUB, ACCESS_TOKEN_SECRET
from app.utils.ecc_tools import verify_hmac_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

mqtt_cli = None
topic_devices = []
running = True


# Callback saat koneksi berhasil
async def on_connect_async(client, userdata, flags, rc):
    try:
        logger.info(f"Connected with result code {rc}")
        devices = await DeviceService.get_active_all_devices("mqtt")
        for device in devices:
            topic_devices.append((MQTT_TOPIC + device.code))
            logger.info(f"device: {device}")
            logger.info(f"topic: {(MQTT_TOPIC + device.code)}")
            client.subscribe(MQTT_TOPIC + device.code, qos=1)
        client.subscribe(MQTT_TOPIC_DEVICE_UNSUB, qos=1)
        client.subscribe(MQTT_TOPIC_DEVICE_SUB, qos=1)
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
            token = data.get("token")
            try:
                if verify_hmac_token(secret=ACCESS_TOKEN_SECRET, token=token,data=):

                token_data = verify_token_device(token=token)
                logger.info(f"token data: {token_data}")
                dt = SensorActuatorCreate(
                    device_id=token_data.device_id,
                    device_code=token_data.device_code,
                    data=data.get("data"),
                    timestamp=datetime.now(tz=pytz.UTC))
                loop = asyncio.get_event_loop()
                asyncio.create_task(process_sensor_data(client, dt, token_data))
            except Exception as e:
                logger.warning(f"Warning on_message: {e}")
        elif msg.topic == MQTT_TOPIC_DEVICE_SUB:
            device_code = payload
            client.subscribe(MQTT_TOPIC + device_code, qos=1)
            logger.info(f"topic sub devices      : {topic_devices}")
            topic_devices.append(MQTT_TOPIC + device_code)
            logger.info(f"topic sub devices after: {topic_devices}")
        elif msg.topic == MQTT_TOPIC_DEVICE_UNSUB:
            device_code = payload
            client.unsubscribe(MQTT_TOPIC + device_code)
            logger.info(f"topic unsub devices      : {topic_devices}")
            topic_devices.remove(MQTT_TOPIC + device_code)
            logger.info(f"topic unsub devices after: {topic_devices}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except Exception as e:
        logger.error(f"Error on_message: {e}")


async def process_sensor_data(client, data: SensorActuatorCreate, token: TokenDataDevice):
    try:
        res = await SensorActuatorService.create_sensor_data(data, token.user_id)
        logger.info(f"res: {res} {type(res)}")
        payload = {
            'id': str(res.id),
            'device_id': res.device_id,
            'device_code': res.device_code
        }
        client.publish(topic=(MQTT_TOPIC_RESPONSE + token.device_code), payload=json.dumps(payload), qos=1)
    except Exception as e:
        logger.error(f"Error on_message: {e}")


# Fungsi untuk memulai MQTT client
async def start_mqtt_client():
    global mqtt_cli
    try:
        logger.info("Starting MQTT client")
        mqtt_cli = mqtt.Client()
        mqtt_cli.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_cli.on_connect = on_connect
        mqtt_cli.on_message = on_message
        logger.info(f"connecting MQTT broker: {MQTT_BROKER} port: {MQTT_PORT}")
        mqtt_cli.connect(MQTT_BROKER, MQTT_PORT, 60)
        while running:
            mqtt_cli.loop(timeout=1)
            await asyncio.sleep(1)
        mqtt_cli.disconnect()
        logger.info("Disconnected")
    except Exception as e:
        logger.error(f"Error in start_mqtt_client: {e}")
