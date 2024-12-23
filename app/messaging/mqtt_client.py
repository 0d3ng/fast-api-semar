# mqtt_client.py
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.services.device_service import DeviceService
from app.utils.config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Callback saat koneksi berhasil
async def on_connect(client, userdata, flags, rc):
    try:
        logger.info(f"Connected with result code {rc}")
        devices = await DeviceService.get_active_all_devices()
        for device in devices:
            client.subscribe(MQTT_TOPIC + device.code, qos=1)
    except Exception as e:
        logger.error(f"Error on_connect: {e}")


# Callback saat pesan diterima
def on_message(client, userdata, msg):
    try:
        logger.info(f"Message received: {msg.payload.decode('utf-8')}")
        data = json.loads(msg.payload.decode('utf-8'))
        # Menyimpan data ke MongoDB menggunakan metode statis dari SensorService
        data['timestamp'] = datetime.now(timezone.utc).timestamp()
        # sensor_service.insert_sensor_data(data=data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except Exception as e:
        logger.error(f"Error on_message: {e}")


# Fungsi untuk memulai MQTT client
def start_mqtt_client():
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Error in start_mqtt_client: {e}")
