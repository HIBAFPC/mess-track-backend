"""Central logging configuration helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


class RequestContextFormatter(logging.Formatter):
    """Readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "method"):
            record.method = "-"
        if not hasattr(record, "path"):
            record.path = "-"
        if not hasattr(record, "status_code"):
            record.status_code = "-"
        if not hasattr(record, "duration_ms"):
            record.duration_ms = "-"
        if not hasattr(record, "user_id"):
            record.user_id = "-"
        if not hasattr(record, "ip"):
            record.ip = "-"
        if not hasattr(record, "error_code"):
            record.error_code = "-"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON formatter for production-safe structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "user_id": getattr(record, "user_id", None),
            "ip": getattr(record, "ip", None),
            "error_code": getattr(record, "error_code", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def build_logging_config(
    *,
    base_dir: Path,
    debug: bool,
    log_level: str = "INFO",
    log_dir_name: str = "logs",
    log_file_name: str = "application.log",
) -> dict[str, Any]:
    """Build a Django LOGGING config with env-aware handlers."""

    log_dir = base_dir / log_dir_name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file_name

    handler_name = "console" if debug else "file"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "readable": {
                "()": "core.logging.RequestContextFormatter",
                "format": (
                    "%(asctime)s %(levelname)s [%(name)s] %(message)s "
                    "request_id=%(request_id)s method=%(method)s path=%(path)s "
                    "status=%(status_code)s duration_ms=%(duration_ms)s "
                    "user_id=%(user_id)s ip=%(ip)s error_code=%(error_code)s"
                ),
            },
            "json": {
                "()": "core.logging.JsonFormatter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "readable",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_file),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
            },
        },
        "loggers": {
            "django": {
                "handlers": [handler_name],
                "level": log_level,
                "propagate": False,
            },
            "mess_track": {
                "handlers": [handler_name],
                "level": log_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": [handler_name],
            "level": log_level,
        },
    }
