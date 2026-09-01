import os
import sys

from loguru import logger

LOGURU_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | "
    "<cyan>{function}</cyan> | "
    "<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

def initialize_setup_logger() -> None:
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        format=LOGURU_FORMAT,
        level="INFO",
        colorize=True,
    )

    logger.add(
        "logs/app.log",
        format=LOGURU_FORMAT,
        level="INFO",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        encoding="utf-8",
    )
    logger.add(
        "logs/error.log",
        format=LOGURU_FORMAT,
        level="ERROR",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        encoding="utf-8",
    )