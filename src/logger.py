import logging
import os
from logging.handlers import RotatingFileHandler


LOG_DIR = "logs"
LOG_FILE = os.path.join(
    LOG_DIR,
    "app.log",
)


def setup_logger():
    """
    Khởi tạo logger.

    Log được:
    - In ra terminal.
    - Lưu vào logs/app.log.
    """

    os.makedirs(
        LOG_DIR,
        exist_ok=True,
    )

    logger = logging.getLogger(
        "event_agent"
    )

    # Tránh tạo logger nhiều lần
    if logger.handlers:
        return logger

    logger.setLevel(
        logging.INFO
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Log ra terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        formatter
    )

    # Log ra file
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    file_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        console_handler
    )

    logger.addHandler(
        file_handler
    )

    return logger


logger = setup_logger()
