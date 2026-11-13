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
FIRMWARE_FOLDER = os.getenv("FIRMWARE_FOLDER")
FIRMWARE_UPDATE_TOPIC = os.getenv("FIRMWARE_UPDATE_TOPIC")

DELAY_AMEDAS = int(os.getenv("DELAY_AMEDAS"))
DELAY_TENKI = int(os.getenv("DELAY_TENKI"))

ENV = os.getenv("ENV")

MESSAGE_BROKER = os.getenv("MESSAGE_BROKER")

GITHUB_DISPATCH_TOKEN = os.getenv("GITHUB_DISPATCH_TOKEN", "")
SEMAR_API_TOKEN = os.getenv("SEMAR_API_TOKEN", "semar_secret_token")
CICD_DISPATCH_MODE = os.getenv("CICD_DISPATCH_MODE", "stub")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "0d3ng")
_raw_repos = os.getenv("GITHUB_REPO_NAMES", "firmware-ota-rolling-key")
GITHUB_REPO_NAMES = [r.strip() for r in _raw_repos.split(",") if r.strip()]
GITHUB_REPO_NAME = GITHUB_REPO_NAMES[0] if GITHUB_REPO_NAMES else "firmware-ota-rolling-key"
GITHUB_WORKFLOW_ID = os.getenv("GITHUB_WORKFLOW_ID", "rotate-key.yml")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "master")
OTA_TELEMETRY_TOPIC = os.getenv("OTA_TELEMETRY_TOPIC", "semar/ota/telemetry")

# AI-Assisted Firmware Security Assessment
SECURITY_GATE_MODE = os.getenv("SECURITY_GATE_MODE", "monitor").strip().lower()
SECURITY_POLICY_PROFILE = os.getenv("SECURITY_POLICY_PROFILE", "lab").strip().lower()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:14b").strip()
LLM_TIMEOUT_S = int(os.getenv("LLM_TIMEOUT_S", "120"))
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "16384"))
NVD_API_KEY = os.getenv("NVD_API_KEY", "").strip()
SECURITY_ENRICH_NETWORK = os.getenv("SECURITY_ENRICH_NETWORK", "true").strip().lower() == "true"
SEMAR_WEB_URL = os.getenv("SEMAR_WEB_URL", "https://web.sinaungoding.com").strip().rstrip("/")
