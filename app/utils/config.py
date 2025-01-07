# config.py
import os
from dotenv import load_dotenv

# Memuat konfigurasi dari file .env
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")
MQTT_TOPIC_RESPONSE = os.getenv("MQTT_TOPIC_RESPONSE")
MQTT_TOPIC_DEVICE_SUB = os.getenv("MQTT_TOPIC_DEVICE_SUB")
MQTT_TOPIC_DEVICE_UNSUB = os.getenv("MQTT_TOPIC_DEVICE_UNSUB")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

MONGO_DB = os.getenv("MONGO_DB")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT"))
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
ACCESS_TOKEN_EXPIRE_DEVICE_DAYS = os.getenv("ACCESS_TOKEN_EXPIRE_DEVICE_DAYS")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH")
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_FILE = os.getenv("LOG_FILE")

ENV = os.getenv("ENV")
