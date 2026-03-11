"""LanceDB database schemas with fastembed embedding function for native hybrid search."""

import os
from functools import cached_property
from typing import Any

from lancedb.embeddings import TextEmbeddingFunction, get_registry, register
from lancedb.pydantic import LanceModel, Vector

EMBEDDING_MODEL_NAME = os.getenv("CANON_EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5-Q")
EMBEDDING_DIM = int(os.getenv("CANON_EMBEDDING_DIM", "768"))
FASTEMBED_THREADS = int(os.getenv("CANON_FASTEMBED_THREADS", "0")) or None
FASTEMBED_BATCH_SIZE = int(os.getenv("CANON_FASTEMBED_BATCH_SIZE", "0")) or None
FASTEMBED_PARALLEL = int(os.getenv("CANON_FASTEMBED_PARALLEL", "0")) or None


@register("fastembed")
class FastEmbedEmbedder(TextEmbeddingFunction):  # type: ignore[misc]
    """Custom LanceDB embedding function using fastembed (ONNX-based, no PyTorch)."""

    model_name: str = EMBEDDING_MODEL_NAME

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        embed_kwargs: dict[str, int] = {}
        if FASTEMBED_BATCH_SIZE is not None:
            embed_kwargs["batch_size"] = FASTEMBED_BATCH_SIZE
        if FASTEMBED_PARALLEL is not None:
            embed_kwargs["parallel"] = FASTEMBED_PARALLEL
        return [embedding.tolist() for embedding in self._model.embed(texts, **embed_kwargs)]

    def ndims(self) -> int:
        """Return embedding dimensions."""
        return EMBEDDING_DIM

    @cached_property
    def _model(self) -> Any:
        """Lazy-load the fastembed model."""
        from fastembed import TextEmbedding

        cache_dir = os.getenv("FASTEMBED_CACHE_PATH")
        return TextEmbedding(self.model_name, cache_dir=cache_dir, threads=FASTEMBED_THREADS)


_embedding_func = get_registry().get("fastembed").create(model_name=EMBEDDING_MODEL_NAME)


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
