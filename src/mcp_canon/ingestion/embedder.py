"""Embedding utilities for mcp-canon.

The embedding model is statically defined in schemas/database.py.
This module provides utilities for direct embedding operations when needed.
"""

from mcp_canon.schemas.database import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL_NAME,
    _embedding_func,
)

# Re-export constants for backward compatibility
DEFAULT_MODEL = EMBEDDING_MODEL_NAME
EMBEDDING_DIMENSIONS = EMBEDDING_DIM


def get_embedding_func() -> object:
    """Get the static embedding function used by LanceDB schemas."""
    return _embedding_func


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using the static model.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (1024 dimensions each)
    """
    return _embedding_func.compute_source_embeddings(texts)  # type: ignore[no-any-return]


def embed_single(text: str) -> list[float]:
    """
    Generate embedding for a single text using the static model.

    Args:
        text: Text string to embed

    Returns:
        Embedding vector (1024 dimensions)
    """
    result = _embedding_func.compute_query_embeddings(text)
    if isinstance(result, list) and len(result) > 0:
        return result[0] if isinstance(result[0], list) else result
    return result  # type: ignore[no-any-return]


class EmbeddingModel:
    """Embedding model wrapper for backward compatibility.

    Note: The model is now static. This class is kept for API compatibility.
    """

    def __init__(self) -> None:
        """Initialize embedding model (uses static model)."""
        self.model_name = EMBEDDING_MODEL_NAME
        self._func = _embedding_func

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return embed_texts(texts)

    def embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        return embed_single(text)
