# mqtt_client.py
import asyncio
import json
import ssl
import struct
import time
from datetime import datetime

import certifi
import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
import pytz

from app.schemas.sensor_actuator_schema import SensorActuatorCreate
from app.schemas.server_schema import ServerResponse
from app.schemas.token_schema import TokenDataDevice
from app.services.device_service import DeviceService
from app.services.sensor_actuator_service import SensorActuatorService
from app.services.server_service import ServerService
from app.services.ota_telemetry_service import OtaTelemetryService
from app.schemas.ota_telemetry_schema import OtaTelemetryCreate

from app.utils.config import OTA_TELEMETRY_TOPIC, ACCESS_TOKEN_SECRET, ENV, MESSAGE_BROKER
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
topic_binary="device/data/encrypted"
topic_binary_response="device/data/decrypted/response"


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
        client.subscribe(topic_binary, qos=qos)
        client.subscribe(OTA_TELEMETRY_TOPIC, qos=qos)
        logger.info(f'Subscribed to OTA telemetry topic: {OTA_TELEMETRY_TOPIC}')
    except Exception as e:
        logger.error(f"Error on_connect: {e}")


# Synchronous wrapper for on_connect
def on_connect(client, userdata, flags, rc):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(on_connect_async(client, userdata, flags, rc), loop)


# Callback saat pesan diterima
def on_message(client, userdata, msg):
    try:
        if msg.topic == topic_binary:
            # Start timing
            start_time = time.perf_counter()

            logger.info(f"Binary message received on topic: {msg.topic}")
            # Handle binary message here
            data = msg.payload
            offset = 0

            # Parse cipher_len (4 bytes, big-endian)
            cipher_len = struct.unpack('>I', data[offset:offset + 4])[0]
            offset += 4

            # Parse cipher
            cipher = data[offset:offset + cipher_len]
            offset += cipher_len

            # Parse tag (16 bytes)
            tag = data[offset:offset + 16]
            offset += 16

            # Parse iv_len (1 byte)
            iv_len = data[offset]
            offset += 1

            # Parse iv
            iv = data[offset:offset + iv_len]
            offset += iv_len

            # Parse aad_len (2 bytes, big-endian)
            aad_len = struct.unpack('>H', data[offset:offset + 2])[0]
            offset += 2

            # Parse aad
            aad = data[offset:offset + aad_len] if aad_len > 0 else b''
            offset += aad_len

            # Parse key_len (1 byte)
            key_len = data[offset]
            offset += 1

            # Parse payload_size (4 bytes, big-endian)
            payload_size = struct.unpack('>I', data[offset:offset + 4])[0]

            # Timing after parsing
            parse_time = time.perf_counter()
            parse_duration = (parse_time - start_time) * 1000  # Convert to milliseconds

            logger.info(f"Received: cipher_len={cipher_len}, key_len={key_len * 8}, payload_size={payload_size}")
            logger.info(f"Parsing took: {parse_duration:.3f} ms")

            # Decrypt
            key = bytes([0xA0 + i for i in range(key_len)])  # Match ESP32 key generation
            aes_cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            aes_cipher.update(aad)
            plaintext = aes_cipher.decrypt_and_verify(cipher, tag)

            # End timing
            end_time = time.perf_counter()
            decrypt_duration = (end_time - parse_time) * 1000  # Decryption time only
            total_duration = (end_time - start_time) * 1000  # Total time

            logger.info(f"Decrypted {len(plaintext)} bytes successfully!")
            logger.info(f"Decryption took: {decrypt_duration:.3f} ms")
            logger.info(f"Total time (receive decrypt): {total_duration:.3f} ms")

            # Create response JSON
            response_data = {
                "status": "success",
                "aes_info": {
                    "mode": "GCM",
                    "key_size": key_len * 8,  # in bits
                    "iv_size": iv_len,
                    "tag_size": len(tag),
                    "cipher_size": cipher_len,
                    "aad_size": aad_len
                },
                "performance": {
                    "parse_duration_ms": round(parse_duration, 3),
                    "decrypt_duration_ms": round(decrypt_duration, 3),
                    "total_duration_ms": round(total_duration, 3)
                },
                "payload": {
                    "original_size": payload_size,
                    "decrypted_size": len(plaintext)
                },
                "timestamp": datetime.now(tz=pytz.UTC).isoformat()
            }

            # Publish response
            response_json = json.dumps(response_data)
            client.publish(topic=topic_binary_response, payload=response_json, qos=1)
            logger.info(f"Response published to {topic_binary_response}")
            logger.info(f"Response data: {response_json}")
            return

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
        elif msg.topic == OTA_TELEMETRY_TOPIC:
            try:
                raw_payload = msg.payload.decode('utf-8')
                logger.info(f"Received OTA telemetry payload: {raw_payload}")
                payload_data = json.loads(raw_payload)
                telemetry_create = OtaTelemetryCreate(**payload_data)
                asyncio.create_task(OtaTelemetryService.create_telemetry(telemetry_create))
            except Exception as e:
                logger.error(f"Failed to process OTA telemetry on {msg.topic}: {e}")
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
        server = await ServerService.get_server_config(protocol=MESSAGE_BROKER.lower(), environment=ENV)
        if not server:
            logger.error(".......................................")
            logger.error(f"Not any server configuration, please create first...")
            logger.error(".......................................")
            running = False
        logger.info(f"server: {server}")

        logger.info("Starting MQTT client")
        ascii_art = r"""
                    .___  ___.   ______     .___________..___________.           
                    |   \/   |  /  __  \    |           ||           |           
                    |  \  /  | |  |  |  |   `---|  |----``---|  |----`           
                    |  |\/|  | |  |  |  |       |  |         |  |                
         __  __  __ |  |  |  | |  `--'  '--.    |  |         |  |     __  __  __ 
        (__)(__)(__)|__|  |__|  \_____\_____\   |__|         |__|    (__)(__)(__)
        """
        logger.info(ascii_art)
        mqtt_cli = mqtt.Client()
        mqtt_cli.username_pw_set(server.parameters['username'], server.parameters['password'])
        mqtt_cli.on_connect = on_connect
        mqtt_cli.on_message = on_message
        if server.protocol == "mqtts":
            logger.info(f"connecting MQTT broker (TLS): {server.host} port: {server.ports['mqtt']}")
            mqtt_cli.tls_set(ca_certs=certifi.where(),tls_version=ssl.PROTOCOL_TLS)
        else:
            logger.info(f"connecting MQTT broker: {server.host} port: {server.ports['mqtt']}")
        mqtt_cli.connect(server.host, server.ports['mqtt'], server.parameters['keep_alive'])
        while running:
            mqtt_cli.loop(timeout=1)
            await asyncio.sleep(1)
        mqtt_cli.disconnect()
        logger.info("Disconnected")
    except Exception as e:
        logger.error(f"Error in start_mqtt_client: {e}")
