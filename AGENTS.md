# AGENTS.md - AI Agent Development Guide

> **Project:** mcp-canon  
> **Purpose:** MCP server providing architectural patterns and best practices to LLM agents via RAG  
> **License:** MIT

---

## Overview of Project

**mcp-canon** is a Model Context Protocol (MCP) server that provides architectural consultant capabilities to AI agents. It uses Retrieval-Augmented Generation (RAG) to serve best practices and coding guidelines from a vector database.

### Key Features
- **Bundled knowledge base** with pre-indexed guides for Python, Docker, Kubernetes, etc.
- **Custom indexing** capability for creating your own knowledge bases from Markdown files
- **HTTP server mode** for remote access and multi-client scenarios
- **Offline-first design** — all data is local, no external API calls required

### Core Architecture
```
┌──────────────────────────────────────────────────────────────────┐
│                     DEV ENVIRONMENT (Indexing)                    │
│  Sources (MD/PDF/URL) → Docling → LangChain Chunking → LanceDB  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                     USER ENVIRONMENT (Runtime)                    │
│  MCP Client → FastMCP Server → SearchEngine → LanceDB Vectors   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technologies

### Language
- **Python 3.11+** (supports 3.11, 3.12, 3.13)

### Main Frameworks & Libraries
| Component | Library | Purpose |
|-----------|---------|---------|
| MCP Protocol | `mcp` | Communication with LLM clients |
| Vector Database | `lancedb` | Embedded vector storage |
| Embeddings | `sentence-transformers` | Text vectorization (nomic-embed, bge-m3) |
| CLI | `typer` | Command-line interface |
| Data Validation | `pydantic` | Schema validation |
| HTTP Server | `uvicorn` + `starlette` | Streamable HTTP (optional) |
| Document Parsing | `docling` | PDF/DOCX/HTML conversion (indexing only) |
| Text Splitting | `langchain-text-splitters` | Markdown chunking (indexing only) |

### Build & Dev Tools
| Tool | Library | Purpose |
|------|---------|---------|
| Package Manager | `uv` | Fast Python package management |
| Build Backend | `hatchling` | Python packaging |
| Linting | `ruff` | Fast Python linter & formatter |
| Type Checking | `mypy` | Static type analysis |
| Testing | `pytest` + `pytest-asyncio` | Async test framework |
| Pre-commit | `pre-commit` | Git hooks |

---

## Commands

### Install
```bash
# Install all dependencies (development mode)
make install
# or
uv sync --all-extras

# Minimal install (runtime only)
pip install mcp-canon

# With indexing support
pip install "mcp-canon[indexing]"

# With HTTP server
pip install "mcp-canon[http]"
```

### Run Tests
```bash
# Run all tests
make test
# or
uv run pytest

# Run with coverage
make test-cov
# or
uv run pytest --cov=src/mcp_canon --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_search_engine.py
```

### Run Lints
```bash
# Lint check
make lint
# or
uv run ruff check src tests

# Format code
make format
# or
uv run ruff format src tests
uv run ruff check --fix src tests

# Type check
make type-check
# or
uv run mypy src

# All checks (lint + type-check + test)
make check

# Pre-commit hooks
make pre-commit
# or
uv run pre-commit run --all-files
```

### Build
```bash
make build
# or
uv build
```

### Clean
```bash
make clean
```

---

## Project Structure

```
canon/
├── src/
│   └── mcp_canon/                 # Main package
│       ├── __init__.py
│       ├── __main__.py           # Entry point for `python -m mcp_canon`
│       ├── logging.py            # Logging configuration
│       ├── py.typed              # PEP 561 marker
│       ├── bundled_db/           # Pre-indexed knowledge base
│       ├── cli/                  # CLI commands
│       │   ├── __init__.py
│       │   └── main.py          # Typer CLI (index, serve, list, validate, info)
│       ├── server/               # MCP server implementation
│       │   ├── __init__.py
│       │   ├── mcp.py           # FastMCP tools and prompts
│       │   └── search.py        # SearchEngine (LanceDB queries)
│       ├── ingestion/            # Knowledge base creation
│       │   ├── __init__.py
│       │   ├── chunker.py       # Markdown text splitting
│       │   ├── discovery.py     # INDEX.md file discovery
│       │   ├── embedder.py      # Vector embedding
│       │   ├── resolver.py      # Content resolution (local/URL)
│       │   ├── summarizer.py    # Guide summarization
│       │   ├── validator.py     # Frontmatter validation
│       │   └── writer.py        # LanceDB writer
│       └── schemas/              # Pydantic models
│           ├── __init__.py
│           ├── database.py      # LanceDB table schemas
│           ├── frontmatter.py   # INDEX.md parsing
│           ├── responses.py     # MCP tool responses
│           └── search.py        # Search result models
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_cli.py              # CLI tests
│   ├── test_http_endpoints.py   # HTTP server tests
│   ├── test_logging.py          # Logging tests
│   ├── test_mcp_tools.py        # MCP tools tests
│   ├── test_schemas.py          # Schema validation tests
│   ├── test_search_engine.py    # Search engine tests
│   ├── test_search_quality.py   # Search quality benchmarks
│   └── test_validator.py        # Validator tests
├── docs/                         # Documentation
│   ├── SYSTEM_DESIGN.md         # Technical architecture
│   ├── PRODUCT_DEFINITION.md    # Product requirements
│   ├── API_SPEC.md              # API specification
│   ├── DATA_TAXONOMY.md         # Data model
│   ├── DEVOPS.md                # DevOps guide
│   ├── MCP_SETUP.md             # MCP client configuration
│   └── TASK.md                  # Development tasks
├── library/                      # Guide sources (for indexing)
│   └── python/                  # Python guides namespace
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI pipeline (lint, type-check, test, build)
│       └── publish.yml          # PyPI publishing
├── Makefile                      # Development commands
├── pyproject.toml                # Project config & dependencies
├── uv.lock                       # Dependency lock file
└── README.md                     # User documentation
```

---

## Application Architecture/Layers

### 1. MCP Protocol Layer (`server/mcp.py`)
- **FastMCP server** exposing tools to LLM clients
- **Tools:** `search_best_practices`, `search_suitable_guides`, `read_full_guide`
- **Prompts:** `code_review`, `implement_feature`, `compare_approaches`
- HTTP endpoints: `/health`, `/ping`

### 2. Search Layer (`server/search.py`)
- **SearchEngine class** for LanceDB queries
- **Hybrid Search:** Vector similarity + metadata filtering
- **Two-stage gating:** Guide relevance check before chunk search
- **RRF Reranking** for result fusion

### 3. Ingestion Layer (`ingestion/`)
- **Discovery:** Scan library for INDEX.md files
- **Validation:** YAML frontmatter parsing
- **Resolution:** Fetch local/remote content
- **Chunking:** Markdown header-based splitting
- **Embedding:** sentence-transformers vectorization
- **Writing:** LanceDB table creation

### 4. Schema Layer (`schemas/`)
- **Pydantic models** for data validation
- **DatabaseSchema:** LanceDB table definitions (guides, chunks, metadata)
- **ResponseSchema:** MCP tool response formats

### 5. CLI Layer (`cli/main.py`)
- **Commands:** `canon index`, `canon serve`, `canon list`, `canon validate`, `canon info`

---

## Style Guide/Coding Conventions

### Python Style
- Target Python version: **3.11**
- Line length: **100 characters**
- Follow **ruff** rules: E, W, F, I, B, C4, UP, ARG, SIM
- Use **type hints** throughout (strict mypy)

### Import Order (isort)
1. Standard library
2. Third-party
3. First-party (`mcp_canon`)

### Naming Conventions
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants

### Docstrings
- Use triple quotes for all public functions/classes
- Include Args, Returns, Raises sections

### Code Example
```python
from mcp_canon.logging import get_logger
from mcp_canon.schemas.responses import GuideSearchResult

logger = get_logger(__name__)


def search_guides(
    query: str,
    namespace: str | None = None,
    limit: int = 5,
) -> list[GuideSearchResult]:
    """
    Search guides by query.

    Args:
        query: Search query string
        namespace: Optional namespace filter
        limit: Maximum results

    Returns:
        List of matching guides
    """
    logger.info("Searching guides", query=query, namespace=namespace)
    ...
```

---

## Testing

### Technologies
- **pytest** (v8+) — test framework
- **pytest-asyncio** — async test support
- **pytest-cov** — coverage reports

### Structure
```
tests/
├── test_cli.py              # CLI command tests
├── test_http_endpoints.py   # HTTP server tests
├── test_logging.py          # Logging behavior tests
├── test_mcp_tools.py        # MCP tool integration tests
├── test_schemas.py          # Pydantic schema tests
├── test_search_engine.py    # SearchEngine unit tests
├── test_search_quality.py   # Search quality benchmarks
└── test_validator.py        # Frontmatter validator tests
```

### Style Guide
- Use `pytest` fixtures for shared setup
- Use `@pytest.mark.asyncio` for async tests
- Descriptive test names: `test_<function>_<scenario>_<expected>`
- Group related tests in classes

### Common Fixtures
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """Create a temporary test database."""
    db_path = tmp_path / "test_db"
    # ... setup ...
    return db_path

@pytest.fixture
def search_engine(sample_db: Path) -> SearchEngine:
    """Create a SearchEngine with test data."""
    return SearchEngine(sample_db)
```

### Running Tests
```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_search_engine.py

# Specific test
uv run pytest tests/test_search_engine.py::test_search_chunks_returns_results

# With verbose output
uv run pytest -v --tb=short

# With coverage
uv run pytest --cov=src/mcp_canon --cov-report=term-missing
```

---

## Solving Typical Tasks

### How to Add a New MCP Tool

1. **Define the tool in `server/mcp.py`:**
```python
@mcp.tool()
def my_new_tool(
    param: str,
    optional_param: int = 10,
) -> MyToolResponse:
    """
    Tool description for LLM.

    Use this tool when:
    - Condition 1
    - Condition 2

    Args:
        param: Description
        optional_param: Description

    Returns:
        Result description
    """
    engine = get_search_engine()
    # ... implementation ...
    return MyToolResponse(...)
```

2. **Add response schema in `schemas/responses.py`:**
```python
class MyToolResponse(BaseModel):
    field: str
    items: list[str]
```

3. **Add tests in `tests/test_mcp_tools.py`:**
```python
def test_my_new_tool():
    result = my_new_tool(param="test")
    assert result.field == "expected"
```

### How to Add a New Guide Namespace

1. **Create directory structure:**
```
library/
└── my-namespace/
    └── my-guide/
        ├── INDEX.md    # Frontmatter metadata
        └── GUIDE.md    # Guide content
```

2. **Create INDEX.md with frontmatter:**
```yaml
---
name: my-guide
description: "Description for semantic search"
metadata:
  tags:
    - tag1
    - tag2
  type: local
---
```

3. **Create GUIDE.md with content:**
```markdown
# My Guide Title

## Section 1
Content...

## Section 2
Content...
```

4. **Index the library:**
```bash
canon index --library ./library --output ./my-db
```

### How to Debug Search Quality

1. **Run quality tests:**
```bash
uv run pytest tests/test_search_quality.py -v
```

2. **Inspect search results:**
```python
from mcp_canon.server.search import SearchEngine

engine = SearchEngine("/path/to/db")
results = engine.search_chunks("my query", limit=10)
for r in results:
    print(f"Score: {r.score:.3f} | Guide: {r.guide_id} | Heading: {r.heading}")
```

3. **Check guide relevance gating:**
```python
guides = engine.search_guides_by_query("my query", min_similarity=0.7)
print(f"Relevant guides: {[g.guide_id for g in guides]}")
```

---

## Instructions

### Creating an Execution Plan

1. **Understand requirements** — read existing docs in `docs/`
2. **Check existing patterns** — review similar code in `src/mcp_canon/`
3. **Write plan** — describe changes file by file
4. **Verify testability** — ensure changes can be tested

### Using Libraries

#### LanceDB
```python
import lancedb
from lancedb.rerankers import RRFReranker

db = lancedb.connect("/path/to/db")
table = db.open_table("chunks")

# Vector search with filter
results = (
    table.search(query_vector)
    .where("namespace = 'python'")
    .limit(5)
    .to_pydantic(ChunkSchema)
)
```

#### sentence-transformers
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
embeddings = model.encode(["text 1", "text 2"])
```

#### Typer CLI
```python
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def my_command(
    path: Annotated[Path, typer.Option("--path", "-p", help="Path to file")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    """Command description."""
    ...
```

#### Logging
```python
from mcp_canon.logging import get_logger

logger = get_logger(__name__)

logger.info("Operation completed", count=10, status="success")
logger.error("Operation failed", error=str(e))
```

---

## Avoid

- **Avoid modifying bundled_db directly** — regenerate via `canon index`
- **Avoid using raw SQL queries** — use LanceDB Python API
- **Avoid skipping type hints** — mypy strict mode is enabled
- **Avoid adding heavy dependencies to core** — use optional extras
- **Avoid ignoring test failures** — CI blocks merge on failures
- **Avoid using print()** — use structured logging
- **Avoid hardcoding paths** — use environment variables (`CANON_DB_PATH`)
- **Avoid changing embedding model** — must match indexed model
- **Avoid creating large chunks** — keep under 8KB for LLM context
- **Avoid forgetting to validate** — run `make check` before committing
