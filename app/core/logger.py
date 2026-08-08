"""
YERİNDE SOC AI
Logger Manager
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.version import APP
from app.core.config import CONFIG

# Log klasörü
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log dosyası
LOG_FILE = LOG_DIR / "yerinde-soc.log"


def get_logger() -> logging.Logger:
    """
    Configure and return the application logger.
    """

    logger = logging.getLogger(APP.name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, CONFIG.log_level, logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Terminal
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # Dosya
    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


LOGGER = get_logger()
