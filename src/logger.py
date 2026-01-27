import logging
import os
import sys
from datetime import datetime

def setup_logger(log_dir="logs", log_level=logging.INFO):
    """
    Configures and returns a logger that outputs to both file and console.
    """
    # Ensure logs directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with date: logs/x_downloader_20231027.log
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"x_downloader_{timestamp}.log")

    # Get or create the logger
    logger = logging.getLogger("x_downloader")
    logger.setLevel(log_level)
    
    # Avoid adding handlers multiple times if setup is called repeatedly
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. File Handler (Detailed with date/time/module)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler (Cleaner for user viewing)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Initialize a default logger instance
logger = setup_logger()
