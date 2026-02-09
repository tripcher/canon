"""MCP tool response schemas."""

from pydantic import BaseModel, Field

# === list_available_guides ===


class GuideInfo(BaseModel):
    """Guide metadata for list responses."""

    id: str = Field(..., description="Guide ID: '{namespace}/{guide_name}'")
    name: str = Field(..., description="Guide name")
    namespace: str = Field(..., description="Technology stack")
    tags: list[str] = Field(..., description="Tags")
    description: str = Field(..., description="Guide description")


class ListGuidesResponse(BaseModel):
    """Response for list_available_guides tool."""

    total: int = Field(..., description="Total number of guides")
    guides: list[GuideInfo] = Field(..., description="List of guide metadata")


# === search_best_practices ===


class SearchResult(BaseModel):
    """Single search result with chunk content."""

    guide_id: str = Field(..., description="Guide ID")
    guide_name: str = Field(..., description="Guide name")
    heading: str = Field(..., description="Section heading")
    heading_path: str = Field(..., description="Full heading path")
    content: str = Field(..., description="Chunk content")
    relevance_score: float = Field(..., description="Similarity score (0-1)")
    char_count: int = Field(..., description="Content character count")


class SearchResultsResponse(BaseModel):
    """Response for search_best_practices tool."""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Number of results returned")
    results: list[SearchResult] = Field(..., description="Search results")


# === search_suitable_guides ===


class GuideSearchResult(BaseModel):
    """Guide search result for description-based search."""

    id: str = Field(..., description="Guide ID")
    name: str = Field(..., description="Guide name")
    namespace: str = Field(..., description="Technology stack")
    tags: list[str] = Field(..., description="Tags")
    description: str = Field(..., description="Guide description")
    relevance_score: float = Field(..., description="Similarity score (0-1)")


class GuidesSearchResponse(BaseModel):
    """Response for search_suitable_guides tool."""

    query: str = Field(..., description="Original search query")
    results: list[GuideSearchResult] = Field(..., description="Matching guides")


# === consult_guide_for_task ===


class TaskConsultResult(BaseModel):
    """Single result from guide consultation."""

    heading: str = Field(..., description="Section heading")
    heading_path: str = Field(..., description="Full heading path")
    content: str = Field(..., description="Section content")
    relevance_score: float = Field(..., description="Similarity score (0-1)")


class TaskConsultResponse(BaseModel):
    """Response for consult_guide_for_task tool."""

    guide_id: str = Field(..., description="Guide that was consulted")
    task: str = Field(..., description="Original task description")
    results: list[TaskConsultResult] = Field(..., description="Relevant sections")


# === read_full_guide ===


class TableOfContentsEntry(BaseModel):
    """Table of contents entry for truncated guides."""

    heading: str = Field(..., description="Section heading")
    level: int = Field(..., description="Heading level (1-6)")


class FullGuideResponse(BaseModel):
    """Response for read_full_guide tool."""

    id: str = Field(..., description="Guide ID")
    name: str = Field(..., description="Guide name")
    namespace: str = Field(..., description="Technology stack")
    tags: list[str] = Field(..., description="Tags")
    description: str = Field(..., description="Guide description")
    content: str | None = Field(None, description="Full guide content (if not truncated)")
    char_count: int = Field(..., description="Total character count")
    truncated: bool = Field(..., description="Whether content was truncated")
    warning: str | None = Field(None, description="Warning message if truncated")
    table_of_contents: list[TableOfContentsEntry] | None = Field(
        None, description="TOC if truncated"
    )
    suggestion: str | None = Field(None, description="Suggestion for using other tools")
