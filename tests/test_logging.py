"""Tests for centralized logging module."""

import json
import logging
import os
from unittest.mock import patch

from mcp_canon.logging import (
    ConsoleFormatter,
    JSONFormatter,
    configure_logging,
    get_logger,
)


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_formats_basic_message(self):
        """Formats basic log message as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_formats_message_with_args(self):
        """Formats log message with arguments."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Value: %s",
            args=("test_value",),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == "Value: test_value"

    def test_includes_extra_fields(self):
        """Includes extra fields like guide_id."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.guide_id = "python/testing"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["guide_id"] == "python/testing"

    def test_includes_source_for_debug(self):
        """Includes source location for DEBUG level."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Debug message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "source" in data
        assert data["source"]["line"] == 10


class TestConsoleFormatter:
    """Test console log formatter."""

    def test_formats_with_level(self):
        """Formats message with level."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "INFO" in result
        assert "test.module" in result
        assert "Test message" in result

    def test_formats_warning_level(self):
        """Formats warning message."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="/path/to/file.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "WARNING" in result


class TestConfigureLogging:
    """Test configure_logging function."""

    def setup_method(self):
        """Reset logging configuration before each test."""
        import mcp_canon.logging as log_module

        log_module._configured = False

    def test_default_level_is_info(self):
        """Default log level is INFO."""
        with patch.dict(os.environ, {}, clear=True):
            configure_logging()
            logger = logging.getLogger("mcp_canon")
            assert logger.level == logging.INFO

    def test_respects_log_level_env(self):
        """Respects CANON_LOG_LEVEL environment variable."""
        import mcp_canon.logging as log_module

        log_module._configured = False

        with patch.dict(os.environ, {"CANON_LOG_LEVEL": "DEBUG"}, clear=True):
            configure_logging()
            logger = logging.getLogger("mcp_canon")
            assert logger.level == logging.DEBUG

    def test_uses_json_formatter_when_enabled(self):
        """Uses JSON formatter when CANON_LOG_JSON=true."""
        import mcp_canon.logging as log_module

        log_module._configured = False

        with patch.dict(os.environ, {"CANON_LOG_JSON": "true"}, clear=True):
            configure_logging()
            logger = logging.getLogger("mcp_canon")
            if logger.handlers:
                handler = logger.handlers[0]
                assert isinstance(handler.formatter, JSONFormatter)

    def test_uses_console_formatter_by_default(self):
        """Uses console formatter by default."""
        import mcp_canon.logging as log_module

        log_module._configured = False

        with patch.dict(os.environ, {"CANON_LOG_JSON": "false"}, clear=True):
            configure_logging()
            logger = logging.getLogger("mcp_canon")
            if logger.handlers:
                handler = logger.handlers[0]
                assert isinstance(handler.formatter, ConsoleFormatter)

    def test_only_configures_once(self):
        """Only configures logging once."""
        import mcp_canon.logging as log_module

        log_module._configured = False

        configure_logging()
        logger = logging.getLogger("mcp_canon")
        original_handlers = len(logger.handlers)

        configure_logging()
        assert len(logger.handlers) == original_handlers


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_logger_instance(self):
        """Returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_returns_named_logger(self):
        """Returns logger with correct name."""
        logger = get_logger("test.module.name")
        assert logger.name == "test.module.name"

    def test_auto_configures_logging(self):
        """Automatically configures logging on first call."""
        import mcp_canon.logging as log_module

        log_module._configured = False

        _logger = get_logger("test")

        assert log_module._configured is True
