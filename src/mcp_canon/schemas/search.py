"""SearchEngine response schemas."""

from pydantic import BaseModel


class GuideListItem(BaseModel):
    """Guide item for list_guides response."""

    id: str
    name: str
    namespace: str
    tags: list[str]
    description: str


class ChunkSearchResult(BaseModel):
    """Chunk search result for search_chunks response."""

    guide_id: str
    guide_name: str
    heading: str
    heading_path: str
    content: str
    relevance_score: float
    char_count: int


class GuideSearchResult(BaseModel):
    """Guide search result for search_guides_by_query response."""

    id: str
    name: str
    namespace: str
    tags: list[str]
    description: str
    relevance_score: float


class TaskSearchResult(BaseModel):
    """Search result for search_within_guide response."""

    heading: str
    heading_path: str
    content: str
    relevance_score: float


class FullGuide(BaseModel):
    """Full guide for get_full_guide response."""

    id: str
    name: str
    namespace: str
    tags: list[str]
    description: str
    content: str
    char_count: int


class DatabaseInfo(BaseModel):
    """Database info for get_database_info response."""

    db_path: str
    initialized: bool
    guides_count: int
    chunks_count: int
    model_name: str
    last_indexed_at: str | None
