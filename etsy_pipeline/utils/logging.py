"""
Structured logging setup for the Etsy pipeline.

Replaces all print() calls with proper structured logging.
Supports two formats:
- 'console': Colored, human-readable output for development
- 'json': Structured JSON lines for production / cloud logging
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class _ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        level = record.levelname.ljust(8)
        name = record.name.split(".")[-1]  # Short module name
        message = record.getMessage()

        formatted = f"{self.BOLD}{timestamp}{self.RESET} {color}{level}{self.RESET} [{name}] {message}"

        if record.exc_info and record.exc_info[1]:
            formatted += f"\n{color}{self.formatException(record.exc_info)}{self.RESET}"

        return formatted


class _JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed via logging calls
        for key in ("job_id", "stage", "worker", "theme", "duration"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO", log_format: str = "console") -> None:
    """
    Configure root logging for the pipeline.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        log_format: 'console' for colored output, 'json' for structured logs.
    """
    root_logger = logging.getLogger("etsy_pipeline")

    # Avoid adding duplicate handlers if called multiple times
    if root_logger.handlers:
        return

    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_ConsoleFormatter())

    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (e.g., 'prompt_worker', 'orchestrator').

    Returns:
        A configured logger instance under the 'etsy_pipeline' namespace.

    Usage:
        from etsy_pipeline.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Starting prompt generation", extra={"job_id": "abc123"})
    """
    return logging.getLogger(f"etsy_pipeline.{name}")
