import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings, get_path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name.split(".")[-1],
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            payload.update(record.extra_data)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(module: str, log_type: str = "system") -> logging.Logger:
    settings = get_settings()
    log_dir = get_path("logs") / log_type
    log_dir.mkdir(parents=True, exist_ok=True)

    logger_name = f"property.{module}"
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    level = getattr(logging, settings["logging"]["level"].upper(), logging.INFO)
    logger.setLevel(level)

    if settings["logging"]["format"] == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        log_dir / f"{today}_{module}.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_event(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "",
        0,
        message,
        (),
        None,
    )
    record.extra_data = kwargs
    logger.handle(record)
