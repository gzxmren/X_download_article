import logging
import os
import sys
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    Custom formatter to output log records as JSON objects.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno
        }
        # Include extra attributes if available (e.g., passed via extra={...})
        if hasattr(record, "url"):
            log_record["url"] = record.url
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logger(log_dir="logs", log_level=logging.INFO):
    """
    Configures and returns a logger that outputs to:
    1. Standard text log file (daily rotated)
    2. Console (stdout)
    3. JSONL structured log file (latest run)
    """
    # Ensure logs directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # 1. Standard Log File: logs/x_downloader_20231027.log
    timestamp = datetime.now().strftime("%Y%m%d")
    text_log_file = os.path.join(log_dir, f"x_downloader_{timestamp}.log")
    
    # 2. JSONL Log File: logs/latest_run.jsonl (Overwrites each run for cleanliness)
    json_log_file = os.path.join(log_dir, "latest_run.jsonl")

    # Get or create the logger
    logger = logging.getLogger("x_downloader")
    logger.setLevel(log_level)
    
    # Avoid adding handlers multiple times if setup is called repeatedly
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- Handler 1: Text File (Detailed) ---
    file_handler = logging.FileHandler(text_log_file, encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # --- Handler 2: Console (Clean) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # --- Handler 3: JSONL File (Structured) ---
    # mode='w' ensures we start fresh each run, easier for parsing 'latest'
    json_handler = logging.FileHandler(json_log_file, mode='w', encoding="utf-8")
    json_handler.setFormatter(JsonFormatter())
    logger.addHandler(json_handler)

    return logger

# Initialize a default logger instance
logger = setup_logger()