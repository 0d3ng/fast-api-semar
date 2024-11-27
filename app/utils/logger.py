import logging
from logging.handlers import RotatingFileHandler
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1000000, backupCount=3)

    # Create formatters and add them to the handlers
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Example usage
logger = get_logger(__name__)
logger.info("Logger is set up and ready to go!")