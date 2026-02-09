import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "guide_id"):
            log_data["guide_id"] = record.guide_id
        if hasattr(record, "query"):
            log_data["query"] = record.query

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add source location for debug
        if record.levelno <= logging.DEBUG:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return (
            f"{color}{timestamp} [{record.levelname:8}]{self.RESET} "
            f"{record.name}: {record.getMessage()}"
        )


_configured = False


def configure_logging() -> None:
    """Configure logging based on environment variables.

    Environment Variables:
        CANON_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        CANON_LOG_JSON: Set to 'true' for JSON format
    """
    global _configured
    if _configured:
        return

    # Get configuration from environment
    log_level_str = os.environ.get("CANON_LOG_LEVEL", "INFO").upper()
    use_json = os.environ.get("CANON_LOG_JSON", "false").lower() == "true"

    # Parse log level
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure root logger for mcp_canon
    root_logger = logging.getLogger("mcp_canon")
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)

    # Set formatter based on environment
    if use_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(handler)

    # Prevent propagation to root logger
    root_logger.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    # Auto-configure on first use
    configure_logging()

    return logging.getLogger(name)
