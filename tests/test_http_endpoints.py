"""Tests for HTTP endpoints (health, ping) added in this session."""

import pytest
from starlette.testclient import TestClient


class TestHTTPEndpoints:
    """Test HTTP endpoints for MCP server."""

    @pytest.fixture
    def client(self):
        """Create test client for the MCP server."""
        from mcp_canon.server.mcp import mcp

        app = mcp.streamable_http_app()
        return TestClient(app)

    def test_ping_returns_pong(self, client):
        """GET /ping returns 'pong' with 200 status."""
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.text == "pong"

    def test_health_returns_healthy_status(self, client):
        """GET /health returns healthy status with JSON."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "canon-mcp"
        assert "database" in data
        assert "initialized" in data["database"]

    def test_health_includes_database_info(self, client):
        """GET /health includes database statistics."""
        response = client.get("/health")
        data = response.json()

        # Database info should always be present
        db_info = data["database"]
        assert isinstance(db_info["initialized"], bool)
        # guides_count is present when initialized
        assert "guides_count" in db_info


class TestMCPEndpoint:
    """Test MCP protocol endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client for the MCP server."""
        from mcp_canon.server.mcp import mcp

        app = mcp.streamable_http_app()
        return TestClient(app)

    def test_root_returns_not_found(self, client):
        """GET / returns 404 (no root handler)."""
        response = client.get("/")
        assert response.status_code == 404
