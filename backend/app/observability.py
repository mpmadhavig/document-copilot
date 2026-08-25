"""Structured, rotating server logs and user-facing error references."""

import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

_FILE_HANDLER_NAME = "document_copilot_backend_file"
_CONSOLE_HANDLER_NAME = "document_copilot_backend_console"
_MAX_LOG_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return message

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": message,
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(log_path: Path, level: str) -> None:
    """Configure application logs once while preserving Uvicorn's handlers."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    existing = next(
        (
            handler
            for handler in root_logger.handlers
            if handler.get_name() == _FILE_HANDLER_NAME
            and isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename) == log_path.resolve()
        ),
        None,
    )
    if existing is None:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=_MAX_LOG_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.set_name(_FILE_HANDLER_NAME)
        file_handler.setLevel(level)
        file_handler.setFormatter(_JsonLogFormatter())
        root_logger.addHandler(file_handler)

    if not any(
        handler.get_name() == _CONSOLE_HANDLER_NAME
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.set_name(_CONSOLE_HANDLER_NAME)
        console_handler.setLevel(level)
        console_handler.setFormatter(_JsonLogFormatter())
        root_logger.addHandler(console_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def new_error_reference() -> str:
    """Return a compact identifier safe to show to an end user."""
    return f"be-{uuid.uuid4().hex[:12]}"
