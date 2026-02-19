"""MCP server implementation using FastMCP."""

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from mcp_canon.ingestion.chunker import extract_table_of_contents
from mcp_canon.logging import get_logger
from mcp_canon.schemas.responses import (
    FullGuideResponse,
    GuidesSearchResponse,
    SearchResult,
    SearchResultsResponse,
    TableOfContentsEntry,
    TaskConsultResponse,
    TaskConsultResult,
)
from mcp_canon.schemas.responses import (
    GuideSearchResult as MCPGuideSearchResult,
)
from mcp_canon.server.search import SearchEngine

# Configure logging
logger = get_logger(__name__)


def get_bundled_db_path() -> Path | None:
    """Get path to bundled database if it exists."""
    try:
        # Check for bundled database in package
        bundled = resources.files("mcp_canon").joinpath("bundled_db")
        # Need to convert to Path - use as_file or check existence
        if bundled.is_dir():
            return Path(str(bundled))
    except (TypeError, FileNotFoundError, AttributeError):
        pass
    return None


def get_db_path() -> Path:
    """Get database path: CANON_DB_PATH env var or bundled DB."""
    # First: check environment variable
    env_path = os.environ.get("CANON_DB_PATH")
    if env_path:
        return Path(env_path)

    # Second: try bundled database (for standard installation)
    bundled = get_bundled_db_path()
    if bundled and bundled.exists():
        return bundled

    # Fallback: return a path that will show "not initialized" message
    return Path("/nonexistent/canon_db")


# Get database path from environment or use default with bundled fallback
DB_PATH = get_db_path()

# Character limit for full guide content
MAX_GUIDE_CHARS = 20000


# Initialize FastMCP server
mcp = FastMCP(
    "Canon",
    instructions="""Canon is an architectural consultant for LLM agents.
It provides curated programming best practices, style guides, and architectural patterns.

## Available Tools

Search:
- search_best_practices: Semantic search for best practices (optionally within a specific guide)
- search_suitable_guides: Find relevant guides for a specific task
- read_full_guide: Get complete guide content (may be truncated for large guides)

## Available Prompts

- code_review: Review code against best practices or a specific guide
- implement_feature: Get step-by-step implementation guidance
- compare_approaches: Compare two architectural approaches objectively

## Recommended Workflow

1. Use search_suitable_guides to find relevant guides for the task
2. Use search_best_practices with guide_id to get specific sections from the best guide
3. Use search_best_practices without guide_id for cross-guide patterns
""",
)


@lru_cache(maxsize=1)
def get_search_engine() -> SearchEngine:
    """Get cached search engine instance."""
    logger.debug("Initializing SearchEngine with db_path=%s", DB_PATH)
    engine = SearchEngine(DB_PATH)
    engine.preload_model()
    return engine


# Health check endpoint for monitoring
@mcp.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health_check(request: Request) -> JSONResponse:  # noqa: ARG001
    """Health check endpoint for load balancers and monitoring systems."""
    try:
        engine = get_search_engine()
        db_info = engine.get_database_info()
        return JSONResponse(
            {
                "status": "healthy",
                "service": "canon-mcp",
                "database": {
                    "initialized": db_info.initialized,
                    "guides_count": db_info.guides_count if db_info.initialized else 0,
                },
            }
        )
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            {"status": "unhealthy", "service": "canon-mcp", "error": str(e)}, status_code=503
        )


# Simple ping endpoint
@mcp.custom_route("/ping", methods=["GET"])  # type: ignore[untyped-decorator]
async def ping(request: Request) -> PlainTextResponse:  # noqa: ARG001
    """Simple ping endpoint for connectivity checks."""
    return PlainTextResponse("pong")


@mcp.tool()
def search_best_practices(
    query: str,
    guide_id: str | None = None,
    namespace: str | None = None,
) -> dict[str, Any]:
    """
    Semantic search for best practices across all guides or within a specific guide.

    Use this tool when:
    - The user asks a conceptual question: "How to hash passwords?"
    - You need to find code patterns or recommendations
    - You want to deep dive into a specific guide (provide guide_id)

    IMPORTANT: Always formulate queries in English for optimal search quality,
    even if the user's question is in another language.

    Args:
        query: Natural language search query in English. Be specific and descriptive.
        guide_id: Optional guide ID to search within (e.g., 'python/django-security').
                  If provided, searches only within this guide (returns top 3 sections).
                  If not provided, searches across all guides (returns top 5 results).
        namespace: Filter by technology (e.g., 'python', 'go'). Ignored if guide_id is set.

    Returns:
        Relevant chunks with content and source information
    """
    try:
        engine = get_search_engine()

        if not engine.is_initialized():
            if guide_id:
                return TaskConsultResponse(
                    guide_id=guide_id,
                    task=query,
                    results=[],
                ).model_dump()
            return SearchResultsResponse(query=query, total_results=0, results=[]).model_dump()

        if guide_id:
            # Deep dive into specific guide
            results = engine.search_chunks(
                query=query,
                guide_id=guide_id,
                limit=3,
            )

            task_results = [
                TaskConsultResult(
                    heading=r.heading,
                    heading_path=r.heading_path,
                    content=r.content,
                    relevance_score=round(r.relevance_score, 2),
                )
                for r in results
            ]

            return TaskConsultResponse(
                guide_id=guide_id,
                task=query,
                results=task_results,
            ).model_dump()
        else:
            # Search across all guides
            results = engine.search_chunks(
                query=query,
                namespace=namespace,
                limit=5,
            )

            search_results = [
                SearchResult(
                    guide_id=r.guide_id,
                    guide_name=r.guide_name,
                    heading=r.heading,
                    heading_path=r.heading_path,
                    content=r.content,
                    relevance_score=round(r.relevance_score, 2),
                    char_count=r.char_count,
                )
                for r in results
            ]

            return SearchResultsResponse(
                query=query,
                total_results=len(search_results),
                results=search_results,
            ).model_dump()
    except ValueError as e:
        logger.warning("Invalid filter value: %s", e)
        if guide_id:
            return {"error": str(e), "guide_id": guide_id, "task": query, "results": []}
        return {"error": str(e), "query": query, "total_results": 0, "results": []}
    except Exception as e:
        logger.exception("search_best_practices failed")
        if guide_id:
            return {
                "error": f"Search failed: {e}",
                "guide_id": guide_id,
                "task": query,
                "results": [],
            }
        return {"error": f"Search failed: {e}", "query": query, "total_results": 0, "results": []}


@mcp.tool()
def search_suitable_guides(
    query: str,
    namespace: str | None = None,
) -> dict[str, object]:
    """
    Find guides that match a task description.

    Use this tool when:
    - You need to find the right guide for a specific task
    - The user describes a problem or goal
    - You want guide-level results, not chunk-level

    IMPORTANT: Always formulate queries in English for optimal search quality,
    even if the user's question is in another language.

    Args:
        query: Description of the task or goal in English
        namespace: Filter by technology

    Returns:
        Top 3 matching guides with descriptions
    """
    try:
        engine = get_search_engine()

        if not engine.is_initialized():
            return GuidesSearchResponse(query=query, results=[]).model_dump()

        results = engine.search_guides_by_query(
            query=query,
            namespace=namespace,
            limit=3,
        )

        guide_results = [
            MCPGuideSearchResult(
                id=r.id,
                name=r.name,
                namespace=r.namespace,
                tags=r.tags,
                description=r.description,
                relevance_score=round(r.relevance_score, 2),
            )
            for r in results
        ]

        return GuidesSearchResponse(query=query, results=guide_results).model_dump()
    except ValueError as e:
        logger.warning("Invalid filter value: %s", e)
        return {"error": str(e), "query": query, "results": []}
    except Exception as e:
        logger.exception("search_suitable_guides failed")
        return {"error": f"Search failed: {e}", "query": query, "results": []}


@mcp.tool()
def read_full_guide(guide_id: str) -> dict[str, object]:
    """
    Get the complete content of a guide.

    Use this tool when:
    - You need the full context of a guide
    - The guide is short and you want everything
    - You're implementing a feature from scratch

    Warning: Large guides (>20k chars) will be truncated.
    Use consult_guide_for_task for specific sections.

    Args:
        guide_id: Guide ID (e.g., 'python/fastapi-production')

    Returns:
        Full guide content or table of contents if truncated
    """
    try:
        engine = get_search_engine()

        if not engine.is_initialized():
            return FullGuideResponse(
                id=guide_id,
                name=guide_id.split("/")[-1] if "/" in guide_id else guide_id,
                namespace=guide_id.split("/")[0] if "/" in guide_id else "",
                tags=[],
                description="Database not initialized",
                content=None,
                char_count=0,
                truncated=False,
                warning="Database not initialized. Run 'canon index' first.",
                table_of_contents=None,
                suggestion="Initialize the database with 'canon index --library /path/to/library'",
            ).model_dump()

        guide = engine.get_full_guide(guide_id)

        if guide is None:
            return FullGuideResponse(
                id=guide_id,
                name=guide_id.split("/")[-1] if "/" in guide_id else guide_id,
                namespace=guide_id.split("/")[0] if "/" in guide_id else "",
                tags=[],
                description="Guide not found",
                content=None,
                char_count=0,
                truncated=False,
                warning=f"Guide '{guide_id}' not found in the database.",
                table_of_contents=None,
                suggestion="Use search_suitable_guides to discover available guides.",
            ).model_dump()

        # Check if content exceeds limit
        if guide.char_count > MAX_GUIDE_CHARS:
            toc = extract_table_of_contents(guide.content)
            toc_entries = [
                TableOfContentsEntry(heading=entry["heading"], level=entry["level"])
                for entry in toc
            ]

            return FullGuideResponse(
                id=guide.id,
                name=guide.name,
                namespace=guide.namespace,
                tags=guide.tags,
                description=guide.description,
                content=None,
                char_count=guide.char_count,
                truncated=True,
                warning=f"Guide exceeds {MAX_GUIDE_CHARS:,} characters. Showing table of contents only.",
                table_of_contents=toc_entries,
                suggestion=f"Use consult_guide_for_task with guide_id='{guide_id}' to search for specific sections.",
            ).model_dump()

        return FullGuideResponse(
            id=guide.id,
            name=guide.name,
            namespace=guide.namespace,
            tags=guide.tags,
            description=guide.description,
            content=guide.content,
            char_count=guide.char_count,
            truncated=False,
            warning=None,
            table_of_contents=None,
            suggestion=None,
        ).model_dump()
    except Exception as e:
        logger.exception("read_full_guide failed")
        return {
            "error": f"Failed to read guide: {e}",
            "id": guide_id,
            "content": None,
            "truncated": False,
        }


# =============================================================================
# MCP Prompts
# =============================================================================

# Common descriptions for reusable parameters
_TECH_STACK_DESC = (
    "Primary technology category (L1 folder in knowledge base). "
    "Examples: 'python', 'go', 'docker', 'kubernetes', 'typescript'. "
    "Used for coarse-grained filtering."
)

_TAGS_DESC = (
    "Semantic filters from controlled vocabulary. "
    "Categories: Frameworks (fastapi, django, flask), "
    "Security (security, authentication, authorization), "
    "Architecture (api, rest, graphql, microservices, async), "
    "Databases (postgresql, mongodb, sqlalchemy), "
    "Testing (testing, unit-testing, mocking), "
    "Deployment (production, performance, monitoring). "
    "Example: ['django', 'security']"
)


@mcp.prompt(title="Code Review")
def code_review(
    code: str = Field(description="The code to review"),
    guide_id: str | None = Field(
        default=None,
        description="Optional guide ID to review against (e.g., 'python/fastapi-production'). If provided, reviews against this specific guide. If not, searches across all guides.",
    ),
    namespace: str = Field(default="python", description=_TECH_STACK_DESC),
    tags: list[str] | None = Field(default=None, description=_TAGS_DESC),
    focus: str = Field(
        default="",
        description="Specific aspect to focus on (e.g., 'error handling', 'security', 'performance')",
    ),
) -> list[base.Message]:
    """
    Review code against Canon's best practices or a specific guide.

    Use this prompt when:
    - You want to review code for adherence to best practices
    - You have a specific guide to check against (provide guide_id)
    - You want to search for relevant patterns (leave guide_id empty)
    """
    focus_section = f"\n\nFocus area: {focus}" if focus else ""

    if guide_id:
        # Targeted mode: review against specific guide
        return [
            base.UserMessage(
                f"""Please review the following code against the guide "{guide_id}".{focus_section}

Use Canon's tools:
1. Use `read_full_guide` with guide_id="{guide_id}" to get the complete guide
2. If the guide is large, use `search_best_practices` with guide_id="{guide_id}" to find relevant sections
3. Compare the code against the guide's recommendations

Code to review:
```
{code}
```

Provide feedback on:
- **Compliance**: Which recommendations from the guide are followed
- **Violations**: Which recommendations are not followed (cite specific sections)
- **Suggestions**: How to improve the code to match the guide
- **Code examples**: Show corrected versions based on the guide"""
            ),
        ]
    else:
        # Search mode: find relevant patterns
        tags_filter = f"\nFilter by tags: {tags}" if tags else ""

        return [
            base.UserMessage(
                f"""Please review the following {namespace} code against best practices.{focus_section}

Use Canon's tools to find relevant architectural patterns and style guides:
1. First, use `search_best_practices` to find relevant patterns
   - namespace: "{namespace}"{tags_filter}
2. Compare the code against the found recommendations
3. Provide specific, actionable feedback

Code to review:
```{namespace}
{code}
```

Provide feedback on:
- **Compliance**: Which recommendations from the best practices are followed
- **Violations**: Which recommendations are not followed (cite specific sections)
- **Suggestions**: How to improve the code to match the best practices
- **Code examples**: Show corrected versions based on the best practices"""
            ),
        ]


@mcp.prompt(title="Implement Feature")
def implement_feature(
    feature: str = Field(description="The feature to implement"),
    guide_id: str | None = Field(
        default=None,
        description="Optional guide ID to follow (e.g., 'python/fastapi-production'). If provided, uses this specific guide. If not, searches across all guides.",
    ),
    namespace: str = Field(default="python", description=_TECH_STACK_DESC),
    tags: list[str] | None = Field(default=None, description=_TAGS_DESC),
    constraints: str = Field(default="", description="Constraints or requirements"),
) -> list[base.Message]:
    """
    Get a step-by-step implementation plan following best practices.

    Use this prompt when:
    - You want to implement a feature correctly from the start
    - You have a specific guide to follow (provide guide_id)
    - You want to search for relevant guides (leave guide_id empty)
    """
    constraints_section = f"\n\nConstraints:\n{constraints}" if constraints else ""

    if guide_id:
        # Targeted mode: use specific guide
        return [
            base.UserMessage(
                f"""I want to implement the following feature following the guide "{guide_id}".

Feature: {feature}{constraints_section}

Use Canon's tools:
1. Use `read_full_guide` with guide_id="{guide_id}" to get the complete guide
2. Use `search_best_practices` with guide_id="{guide_id}" and query="{feature}" to find relevant sections
3. Extract implementation patterns from the guide

Provide:
- **Step-by-step implementation plan** based on the guide
- **Code examples** directly from or inspired by the guide
- **Key patterns** from the guide that apply to this feature
- **Common pitfalls** mentioned in the guide to avoid
- **Testing recommendations** from the guide"""
            ),
        ]
    else:
        # Search mode: find relevant guides
        tags_filter = f"\n   - tags: {tags}" if tags else ""

        return [
            base.UserMessage(
                f"""I want to implement the following feature using {namespace} best practices.

Feature: {feature}{constraints_section}

Please use Canon's tools to create an implementation plan:
1. Use `search_suitable_guides` to find relevant guides
   - namespace: "{namespace}"{tags_filter}
2. Use `search_best_practices` for specific patterns
3. Use `search_best_practices` with guide_id for detailed implementation guidance from the suitable guide

Provide:
- **Step-by-step implementation plan**
- **Code examples** following the patterns from guides
- **Key patterns** from the suitable guide and best practices that apply to this feature
- **Common pitfalls** to avoid (from the guides)
- **Testing recommendations**"""
            ),
        ]


@mcp.prompt(title="Compare Approaches")
def compare_approaches(
    approach_a: str = Field(
        description="First approach (e.g., 'sync handlers', 'REST API', 'SQLAlchemy ORM')"
    ),
    approach_b: str = Field(
        description="Second approach (e.g., 'async handlers', 'GraphQL', 'raw SQL')"
    ),
    namespace: str | None = Field(
        default=None,
        description=_TECH_STACK_DESC + " Optional — leave empty to search all.",
    ),
    tags: list[str] | None = Field(default=None, description=_TAGS_DESC),
    context: str = Field(default="", description="Context for the comparison"),
) -> list[base.Message]:
    """
    Compare two architectural approaches using Canon's knowledge base.

    Use this prompt when:
    - You need to choose between two approaches
    - You want an objective comparison based on best practices
    - You're evaluating trade-offs
    """
    context_section = f"\n\nContext: {context}" if context else ""
    tech_filter = f'\n   - namespace: "{namespace}"' if namespace else ""
    tags_filter = f"\n   - tags: {tags}" if tags else ""

    return [
        base.UserMessage(
            f"""Please compare these two approaches:{context_section}

**Approach A**: {approach_a}
**Approach B**: {approach_b}

Use Canon's tools to find relevant information:
1. Use `search_best_practices` to find patterns for each approach{tech_filter}{tags_filter}
2. Look for guides that discuss these approaches

Provide a structured comparison:
- **Overview**: Brief description of each approach
- **Pros and Cons**: For each approach
- **When to use each**: Recommended scenarios
- **Recommendation**: Which to choose based on the guides and context"""
        ),
    ]


def main() -> None:
    """Entry point for uvx mcp-canon (STDIO mode)."""
    mcp.run()


# Entry point for running the server
if __name__ == "__main__":
    main()
