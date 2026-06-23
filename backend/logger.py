import logging
import os

# Define the directory where logs will be stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, "app.log")

# Setup a clean log formatter matching standard production patterns
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Setup File Handler (writes to app.log with UTF-8 encoding)
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Setup Console Handler (writes to stdout)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Initialize application-wide logger
logger = logging.getLogger("flexurl")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if the script is imported multiple times
if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(file_handler)
logger.addHandler(console_handler)
