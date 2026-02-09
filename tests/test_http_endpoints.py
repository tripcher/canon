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

    def test_health_returns_structured_response(self, client):
        """GET /health returns structured JSON response."""
        response = client.get("/health")
        # Accept both 200 (healthy) and 503 (unhealthy, e.g. no DB in CI)
        assert response.status_code in (200, 503)

        data = response.json()
        assert data["service"] == "canon-mcp"
        assert data["status"] in ("healthy", "unhealthy")

    def test_health_includes_database_info_when_healthy(self, client):
        """GET /health includes database info when DB is available."""
        response = client.get("/health")
        data = response.json()

        if response.status_code == 200:
            # When healthy, database info should be present
            assert "database" in data
            db_info = data["database"]
            assert isinstance(db_info["initialized"], bool)
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
