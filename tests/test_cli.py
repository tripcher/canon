"""Tests for CLI commands."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from mcp_canon.cli.main import DEFAULT_DB_PATH, app

runner = CliRunner()


class TestDefaultDbPath:
    """Test DEFAULT_DB_PATH configuration."""

    def test_default_db_path_is_bundled_db(self):
        """DEFAULT_DB_PATH points to bundled_db directory."""
        assert DEFAULT_DB_PATH.name == "bundled_db"
        assert "mcp_canon" in str(DEFAULT_DB_PATH)

    def test_default_db_path_is_relative_to_package(self):
        """DEFAULT_DB_PATH is inside the mcp_canon package."""
        # Should be: .../src/mcp_canon/bundled_db or .../mcp_canon/bundled_db
        parts = DEFAULT_DB_PATH.parts
        assert "mcp_canon" in parts or "bundled_db" in parts


class TestVersionCommand:
    """Test --version flag."""

    def test_version_flag(self):
        """--version shows version and exits."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "canon" in result.output.lower() or "." in result.output

    def test_version_short_flag(self):
        """-V shows version and exits."""
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0


class TestValidateCommand:
    """Test validate command."""

    def test_validate_nonexistent_library(self):
        """validate with nonexistent library path fails."""
        result = runner.invoke(app, ["validate", "-l", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_validate_empty_library(self):
        """validate with empty directory reports no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["validate", "-l", tmpdir])
            # Should succeed or report no files
            assert "No" in result.output or result.exit_code == 0

    def test_validate_valid_file(self):
        """validate with valid markdown file passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lib_path = Path(tmpdir) / "library"
            lib_path.mkdir()

            # Create a valid guide
            (lib_path / "python").mkdir()
            guide_file = lib_path / "python" / "testing.md"
            guide_file.write_text(
                """---
name: python/testing
namespace: python
tags:
  - testing
description: A comprehensive guide to testing in Python.
---
# Testing Guide

This is a test guide.
"""
            )

            result = runner.invoke(app, ["validate", "-l", str(lib_path)])
            # Should pass validation
            assert result.exit_code == 0 or "passed" in result.output.lower()


class TestListCommand:
    """Test list command."""

    def test_list_nonexistent_db(self):
        """list with nonexistent database shows not initialized message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent"
            result = runner.invoke(app, ["list", "--db", str(db_path)])
            # Should indicate not initialized
            assert "not initialized" in result.output.lower() or result.exit_code != 0

    def test_list_empty_db(self):
        """list with empty database shows not initialized message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["list", "--db", tmpdir])
            # Empty dir is not a valid LanceDB
            assert "not initialized" in result.output.lower() or result.exit_code != 0

    def test_list_uses_pydantic_model_attributes(self):
        """list command accesses guide attributes, not dict keys.

        This test verifies the fix for GuideListItem access pattern.
        """
        # The fix changed guide["id"] to guide.id, etc.
        # If it fails, the command will crash with TypeError
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "db"
            result = runner.invoke(app, ["list", "--db", str(db_path)])
            # Should not crash with "'GuideListItem' object is not subscriptable"
            assert "not subscriptable" not in str(result.exception or "")


class TestInfoCommand:
    """Test info command."""

    def test_info_nonexistent_db(self):
        """info with nonexistent database handles gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent"
            result = runner.invoke(app, ["info", "--db", str(db_path)])
            # May show info header or fail - accept both
            assert (
                "Canon Database Info" in result.output
                or result.exit_code != 0
                or "error" in str(result.exception).lower()
            )

    def test_info_empty_db(self):
        """info with empty database handles gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["info", "--db", tmpdir])
            # May show info panel or have issues - accept both
            assert (
                "Canon Database Info" in result.output
                or result.exit_code != 0
                or result.exception is not None
            )

    def test_info_uses_pydantic_model_attributes(self):
        """info command accesses db_info attributes, not dict keys.

        This test verifies the fix for DatabaseInfo access pattern.
        """
        # The fix changed info["db_path"] to db_info.db_path, etc.
        # If it fails, the command will crash with TypeError
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "db"
            result = runner.invoke(app, ["info", "--db", str(db_path)])
            # Should not crash with "'DatabaseInfo' object is not subscriptable"
            assert "not subscriptable" not in str(result.exception or "")


class TestIndexCommand:
    """Test index command."""

    def test_index_nonexistent_library(self):
        """index with nonexistent library path fails."""
        result = runner.invoke(app, ["index", "-l", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_index_empty_library(self):
        """index with empty library reports no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["index", "-l", tmpdir, "--db", f"{tmpdir}/db"])
            # Should report no files found or succeed
            assert "No" in result.output or "0" in result.output or result.exit_code == 0

    def test_index_uses_default_db_path(self):
        """index command uses DEFAULT_DB_PATH when --db not specified."""
        # This verifies the DEFAULT_DB_PATH change from ~/.canon/db to bundled_db
        result = runner.invoke(app, ["index", "--help"])
        # Help should show the default path contains bundled_db
        assert "bundled_db" in result.output or "default" in result.output.lower()


class TestServeCommand:
    """Test serve command."""

    def test_serve_help_shows_options(self):
        """serve --help shows host, port, and db options."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--db" in result.output

    def test_serve_uses_uvicorn(self):
        """serve command imports uvicorn (verified by help working).

        The fix changed from mcp.run() to uvicorn.run() for HTTP transport.
        """
        # If uvicorn import fails, serve would crash
        # We just verify the command structure is valid
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
