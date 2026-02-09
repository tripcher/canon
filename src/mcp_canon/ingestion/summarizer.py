"""Extractive summarization for guides using semantic centroid selection."""

import numpy as np

from mcp_canon.schemas.database import ChunkSchema, _embedding_func


def extractive_summary_from_chunks(
    chunks: list[ChunkSchema],
    ratio: float = 0.10,
    min_chunks: int = 2,
    max_chunks: int = 10,
) -> str:
    """
    Generate extractive summary using semantic centroid selection.

    Computes embeddings for all chunks, finds the semantic centroid,
    and selects chunks closest to the centroid.

    Args:
        chunks: List of ChunkSchema objects
        ratio: Fraction of chunks to include (default 10%)
        min_chunks: Minimum chunks in summary
        max_chunks: Maximum chunks in summary

    Returns:
        Concatenated summary from selected chunks
    """
    if not chunks:
        return ""

    if len(chunks) <= min_chunks:
        return "\n\n".join(c.content for c in chunks)

    # Generate embeddings for all chunks
    texts = [c.content for c in chunks]
    vectors = np.array(_embedding_func.compute_source_embeddings(texts))

    # Calculate K based on ratio
    k = max(min_chunks, min(max_chunks, int(len(chunks) * ratio)))

    # Compute centroid (mean of all vectors)
    centroid = vectors.mean(axis=0)

    # Calculate distances to centroid
    distances = np.linalg.norm(vectors - centroid, axis=1)

    # Select top-K closest to centroid (most representative)
    closest_indices = np.argsort(distances)[:k]

    # Sort by original order to preserve document flow
    top_indices = sorted(int(i) for i in closest_indices)

    return "\n\n".join(chunks[i].content for i in top_indices)


def extract_headings(chunks: list[ChunkSchema]) -> str:
    """
    Extract unique headings from chunks in order.

    Args:
        chunks: List of ChunkSchema objects

    Returns:
        Newline-separated unique headings
    """
    seen: set[str] = set()
    headings: list[str] = []

    for chunk in chunks:
        if chunk.heading and chunk.heading not in seen:
            seen.add(chunk.heading)
            headings.append(chunk.heading)

    return "\n".join(headings)
