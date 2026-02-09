"""Ingestion engine for indexing knowledge library."""

from mcp_canon.ingestion.chunker import chunk_content
from mcp_canon.ingestion.discovery import discover_guides
from mcp_canon.ingestion.embedder import EmbeddingModel, embed_single, embed_texts
from mcp_canon.ingestion.resolver import resolve_content
from mcp_canon.ingestion.summarizer import extract_headings, extractive_summary_from_chunks
from mcp_canon.ingestion.validator import parse_frontmatter, validate_frontmatter
from mcp_canon.ingestion.writer import DatabaseWriter

__all__ = [
    "discover_guides",
    "parse_frontmatter",
    "validate_frontmatter",
    "resolve_content",
    "chunk_content",
    "embed_texts",
    "embed_single",
    "EmbeddingModel",
    "DatabaseWriter",
    "extractive_summary_from_chunks",
    "extract_headings",
]
