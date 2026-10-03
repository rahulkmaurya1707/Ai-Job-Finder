import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "job_finder.log"

_LOGGING_INITIALIZED = False


def setup_logging(
    log_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configures Python's logging module with a RotatingFileHandler and Console StreamHandler."""
    global _LOGGING_INITIALIZED

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()

    if _LOGGING_INITIALIZED:
        return root_logger

    root_logger.setLevel(log_level)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Rotating File Handler (Max 5MB per file, keeping 5 backup files)
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 2. Console Handler with UTF-8 encoding safeguard for Windows
    console_stream = sys.stdout
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    console_handler = logging.StreamHandler(console_stream)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Clear pre-existing handlers to prevent duplicate logging
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _LOGGING_INITIALIZED = True
    return root_logger


def get_logger(name: str = "job_finder") -> logging.Logger:
    """Return a logger instance configured with RotatingFileHandler."""
    setup_logging()
    return logging.getLogger(name)
