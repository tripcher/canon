"""MCP server module."""

from mcp_canon.server.mcp import mcp
from mcp_canon.server.search import SearchEngine

__all__ = ["mcp", "SearchEngine"]
