"""LanceDB database schemas with embedded embedding function for native hybrid search."""

from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

# Static embedding model - cannot be overridden
# Using nomic-embed-text-v1.5: 768 dims, English, 8192 tokens context, 0.5 GB
EMBEDDING_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
EMBEDDING_DIM = 768

_embedding_func = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)


class ChunkSchema(LanceModel):  # type: ignore[misc]
    """Schema for content chunks table in LanceDB with auto-embedding."""

    id: str
    guide_id: str
    namespace: str
    tags: list[str]
    heading: str
    heading_path: str
    content: str = _embedding_func.SourceField()  # Source for embedding
    chunk_index: int
    char_count: int
    vector: Vector(EMBEDDING_DIM) = _embedding_func.VectorField()  # type: ignore[valid-type]


class GuideSchema(LanceModel):  # type: ignore[misc]
    """Metadata schema for guides table in LanceDB with auto-embedding."""

    id: str
    name: str
    namespace: str
    tags: list[str]
    description: str
    source_type: str
    source_url: str | None = None
    file_path: str
    content_hash: str
    indexed_at: str
    # Multi-vector search fields
    summary: str = _embedding_func.SourceField()  # Extractive summary (10% of content)
    summary_vector: Vector(EMBEDDING_DIM) = _embedding_func.VectorField(default=None)  # type: ignore[valid-type]
    headings: str  # Concatenated chunk headings (FTS indexed)


class DatabaseMetadata(LanceModel):  # type: ignore[misc]
    """Metadata about the vector database."""

    model_name: str = EMBEDDING_MODEL_NAME
    model_dimensions: int = EMBEDDING_DIM
    created_at: str
    last_indexed_at: str
    library_path: str
