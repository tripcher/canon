"""Content chunking with hybrid strategy: small H2 sections whole, large ones split by H3."""

import re
from dataclasses import dataclass, field
from typing import Any

# H2 sections smaller than this are kept as single chunks
CHUNK_SIZE_THRESHOLD = 5000


@dataclass
class Chunk:
    """A semantic chunk from markdown content."""

    content: str
    heading: str
    heading_path: str
    chunk_index: int
    char_count: int


@dataclass
class _RawChunk:
    """Internal chunk with header level info for grouping."""

    content: str
    heading: str
    heading_path: str
    h1: str = ""
    h2: str = ""
    h3: str = ""
    h4: str = ""


@dataclass
class _H2Section:
    """A section grouped by H2 header."""

    h2_heading: str
    h1_heading: str
    chunks: list[_RawChunk] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return sum(len(c.content) for c in self.chunks)


def chunk_content(
    content: str,
    _guide_id: str,
) -> list[Chunk]:
    """
    Split markdown content into semantic chunks using hybrid strategy.

    Strategy:
    - Small H2 sections (< 2000 chars): Keep as single chunk
    - Large H2 sections (>= 2000 chars): Split by H3 subsections

    Args:
        content: Markdown content to split
        guide_id: Guide ID for metadata

    Returns:
        List of chunks with heading information
    """
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except ImportError as e:
        raise ImportError(
            "Chunking requires the 'indexing' extra. "
            "Install with: pip install 'mcp-canon[indexing]'"
        ) from e

    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    documents = splitter.split_text(content)

    # Phase 1: Convert to raw chunks with header metadata
    raw_chunks: list[_RawChunk] = []
    for doc in documents:
        chunk_text = doc.page_content.strip()
        if not chunk_text:
            continue

        h1 = doc.metadata.get("h1", "")
        h2 = doc.metadata.get("h2", "")
        h3 = doc.metadata.get("h3", "")
        h4 = doc.metadata.get("h4", "")

        parts = [p for p in [h1, h2, h3, h4] if p]
        heading_path = " > ".join(parts) if parts else "Introduction"
        heading = parts[-1] if parts else "Introduction"

        raw_chunks.append(
            _RawChunk(
                content=chunk_text,
                heading=heading,
                heading_path=heading_path,
                h1=h1,
                h2=h2,
                h3=h3,
                h4=h4,
            )
        )

    # Phase 2: Group by H2 sections
    h2_sections = _group_by_h2(raw_chunks)

    # Phase 3: Apply hybrid strategy
    final_chunks: list[Chunk] = []
    chunk_index = 0

    for section in h2_sections:
        if section.total_chars < CHUNK_SIZE_THRESHOLD:
            # Merge all chunks in this H2 section
            merged = _merge_section(section)
            final_chunks.append(
                Chunk(
                    content=merged.content,
                    heading=merged.heading,
                    heading_path=merged.heading_path,
                    chunk_index=chunk_index,
                    char_count=len(merged.content),
                )
            )
            chunk_index += 1
        else:
            # Keep H3-level granularity for large sections
            for raw in section.chunks:
                final_chunks.append(
                    Chunk(
                        content=raw.content,
                        heading=raw.heading,
                        heading_path=raw.heading_path,
                        chunk_index=chunk_index,
                        char_count=len(raw.content),
                    )
                )
                chunk_index += 1

    return final_chunks


def _group_by_h2(chunks: list[_RawChunk]) -> list[_H2Section]:
    """Group raw chunks by their H2 header."""
    sections: list[_H2Section] = []
    current_section: _H2Section | None = None

    for chunk in chunks:
        h2_key = chunk.h2 or "(no-h2)"

        if current_section is None or current_section.h2_heading != h2_key:
            current_section = _H2Section(
                h2_heading=h2_key,
                h1_heading=chunk.h1,
            )
            sections.append(current_section)

        current_section.chunks.append(chunk)

    return sections


def _merge_section(section: _H2Section) -> _RawChunk:
    """Merge all chunks in a section into one."""
    if not section.chunks:
        return _RawChunk(content="", heading="", heading_path="")

    merged_content = "\n\n".join(c.content for c in section.chunks)

    # Use the H2 heading as the main heading
    h2 = section.h2_heading if section.h2_heading != "(no-h2)" else ""
    parts = [p for p in [section.h1_heading, h2] if p]
    heading_path = " > ".join(parts) if parts else "Introduction"
    heading = h2 or section.h1_heading or "Introduction"

    return _RawChunk(
        content=merged_content,
        heading=heading,
        heading_path=heading_path,
        h1=section.h1_heading,
        h2=h2,
    )


def extract_table_of_contents(content: str) -> list[dict[str, Any]]:
    """
    Extract table of contents from markdown content.

    Args:
        content: Markdown content

    Returns:
        List of TOC entries with heading and level
    """
    toc: list[dict[str, Any]] = []
    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    for match in header_pattern.finditer(content):
        level = len(match.group(1))
        heading = match.group(2).strip()
        toc.append({"heading": heading, "level": level})

    return toc
