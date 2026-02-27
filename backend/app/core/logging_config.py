"""Centralized logging configuration.

Sets up file-based logging with rotation alongside the existing console output.
All ``app.*`` loggers inherit the configured handlers automatically.

Usage (called once in main.py):
    from app.core.logging_config import setup_logging
    setup_logging("INFO")
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5


def setup_logging(level: str = "INFO") -> None:
    """Configure application-wide logging.

    - RotatingFileHandler → ``backend/logs/app.log`` (5 MB, 5 backups)
    - StreamHandler → stdout (preserves existing console output)
    - Attaches to the ``app`` logger and ``uvicorn`` / ``uvicorn.access`` loggers
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # Configure the root "app" logger — all app.* modules inherit this.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)

    # Also capture uvicorn logs into the same file.
    for uvicorn_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uvicorn_name)
        uv_logger.addHandler(file_handler)
