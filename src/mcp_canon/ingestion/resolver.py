"""Content resolution for local and remote sources."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from mcp_canon.schemas.frontmatter import GuideFrontmatter


@dataclass
class ResolvedContent:
    """Resolved guide content."""

    content: str
    source_path: str
    is_remote: bool = False


def resolve_content(
    frontmatter: GuideFrontmatter,
    guide_dir: Path,
) -> ResolvedContent:
    """
    Resolve guide content based on frontmatter type.

    For type: local, read GUIDE.md from the guide directory.
    For type: link, fetch and convert remote content (requires indexing extra).

    Args:
        frontmatter: Parsed frontmatter with type and url
        guide_dir: Directory containing the guide

    Returns:
        ResolvedContent with markdown content
    """
    if frontmatter.metadata.type == "local":
        return _resolve_local(guide_dir)
    else:
        return _resolve_remote(frontmatter)


def _resolve_local(guide_dir: Path) -> ResolvedContent:
    """Read local GUIDE.md file."""
    guide_path = guide_dir / "GUIDE.md"

    if not guide_path.exists():
        # If no GUIDE.md, use content from INDEX.md (after frontmatter)
        index_path = guide_dir / "INDEX.md"
        content = index_path.read_text(encoding="utf-8")

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return ResolvedContent(content=content, source_path=str(index_path))

    content = guide_path.read_text(encoding="utf-8")
    return ResolvedContent(content=content, source_path=str(guide_path))


def _resolve_remote(frontmatter: GuideFrontmatter) -> ResolvedContent:
    """
    Fetch and convert remote content.

    This requires the indexing extra dependencies (httpx, docling).
    """
    url = frontmatter.metadata.url
    if url is None:
        raise ValueError("URL is required for remote content")

    format_type = frontmatter.metadata.format

    try:
        import httpx
    except ImportError as e:
        raise ImportError(
            "Remote content resolution requires the 'indexing' extra. "
            "Install with: pip install 'mcp-canon[indexing]'"
        ) from e

    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()

    if format_type == "markdown":
        # Direct markdown, no conversion needed
        return ResolvedContent(content=response.text, source_path=url, is_remote=True)

    # For other formats (html, pdf, docx), use Docling for conversion
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as e:
        raise ImportError(
            "Document conversion requires the 'indexing' extra. "
            "Install with: pip install 'mcp-canon[indexing]'"
        ) from e

    converter = DocumentConverter()

    # Save to temp file for Docling
    suffix_map = {
        "html": ".html",
        "pdf": ".pdf",
        "docx": ".docx",
    }
    suffix = suffix_map.get(format_type or "html", ".html")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        result = converter.convert(tmp_path)
        markdown = result.document.export_to_markdown()
        return ResolvedContent(content=markdown, source_path=url, is_remote=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
