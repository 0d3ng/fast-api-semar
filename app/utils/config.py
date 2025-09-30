# config.py
import os
from dotenv import load_dotenv

# Memuat konfigurasi dari file .env
load_dotenv()

MONGO_DB = os.getenv("MONGO_DB")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT"))
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")
MONGO_URL = os.getenv("MONGO_URL")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
ACCESS_TOKEN_EXPIRE_DEVICE_DAYS = os.getenv("ACCESS_TOKEN_EXPIRE_DEVICE_DAYS")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH")
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_FILE = os.getenv("LOG_FILE")
FIRMWARE_FOLDER = os.getenv("FIRMWARE_FOLDER")
FIRMWARE_UPDATE_TOPIC = os.getenv("FIRMWARE_UPDATE_TOPIC")

DELAY_AMEDAS = int(os.getenv("DELAY_AMEDAS"))
DELAY_TENKI = int(os.getenv("DELAY_TENKI"))

ENV = os.getenv("ENV")
