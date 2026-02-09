"""Pydantic schemas for mcp-canon."""

from mcp_canon.schemas.database import ChunkSchema, DatabaseMetadata, GuideSchema
from mcp_canon.schemas.frontmatter import GuideFrontmatter, GuideMetadata
from mcp_canon.schemas.responses import (
    FullGuideResponse,
    GuideInfo,
    GuidesSearchResponse,
    ListGuidesResponse,
    SearchResult,
    SearchResultsResponse,
    TaskConsultResponse,
    TaskConsultResult,
)
from mcp_canon.schemas.search import (
    ChunkSearchResult,
    DatabaseInfo,
    FullGuide,
    GuideListItem,
    GuideSearchResult,
    TaskSearchResult,
)

__all__ = [
    # Frontmatter
    "GuideFrontmatter",
    "GuideMetadata",
    # Database
    "GuideSchema",
    "ChunkSchema",
    "DatabaseMetadata",
    # MCP Responses
    "GuideInfo",
    "ListGuidesResponse",
    "SearchResult",
    "SearchResultsResponse",
    "GuidesSearchResponse",
    "TaskConsultResult",
    "TaskConsultResponse",
    "FullGuideResponse",
    # SearchEngine Returns
    "GuideListItem",
    "ChunkSearchResult",
    "GuideSearchResult",
    "TaskSearchResult",
    "FullGuide",
    "DatabaseInfo",
]
