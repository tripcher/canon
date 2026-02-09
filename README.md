# mcp-canon

MCP server providing architectural patterns and best practices to LLM agents via RAG.

## Installation

### Standard (with bundled guides)
```bash
pip install mcp-canon
```
Includes pre-populated database with best practices for Python, Docker, Kubernetes, etc.

### With indexing support
```bash
pip install "mcp-canon[indexing]"
```
Required for creating your own knowledge base from Markdown files.

### With HTTP server support
```bash
pip install "mcp-canon[http]"
```

### Development (all dependencies)
```bash
pip install "mcp-canon[dev]"
```

---

## Quick Start

### Option 1: Using bundled guides (zero configuration)

Just install and configure your MCP client — the bundled database works immediately.

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

---

### Option 2: Create and index your own guides

Complete workflow from installation to running with custom guides.

#### Step 1: Install with indexing support

```bash
pip install "mcp-canon[indexing]"
```

#### Step 2: Create library structure

```
my-library/
├── python/
│   └── fastapi-guide/
│       ├── INDEX.md      # Required: metadata
│       └── GUIDE.md      # Content
└── docker/
    └── best-practices/
        └── INDEX.md      # Can reference external URL
```

#### Step 3: Create INDEX.md with frontmatter

```bash
mkdir -p my-library/python/fastapi-guide
```

Create `my-library/python/fastapi-guide/INDEX.md`:

```yaml
---
name: fastapi-guide
description: "Production-ready FastAPI patterns and best practices"
metadata:
  tags:
    - python
    - fastapi
    - api
    - production
  type: local
---
```

#### Step 4: Add guide content

Create `my-library/python/fastapi-guide/GUIDE.md`:

```markdown
# FastAPI Production Guide

## Project Structure
...

## Error Handling
...
```

#### Step 5: Index your library

```bash
# Index to custom location
canon index --library ./my-library --output /path/to/my-db

# Validate frontmatter before indexing (optional)
canon validate --library ./my-library
```

#### Step 6: Configure MCP client

**Local mcp** 

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"],
      "env": {
        "CANON_DB_PATH": "/path/to/my-db"
      }
    }
  }
}
```

### Option 3: Running as HTTP server

For remote access or multi-client scenarios, run Canon as an HTTP server.

#### Step 1: Install with HTTP support

```bash
pip install "mcp-canon[http]"
```

#### Step 2: Start the server

```bash
# Default port 8080
canon serve

# Custom port and host
canon serve --port 3000 --host 0.0.0.0

# With custom database
CANON_DB_PATH=/path/to/db canon serve --port 8080
```

#### Step 3: Configure MCP client

```json
{
  "mcpServers": {
    "canon": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

#### Step 4: Verify connection

```bash
# Health check
curl http://localhost:8080/health
```

## MCP Client Configuration

Configuration examples for popular MCP clients. Replace `CANON_DB_PATH` with your database path if using a custom database.

### Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

With custom database:
```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"],
      "env": {
        "CANON_DB_PATH": "/path/to/your/db"
      }
    }
  }
}
```

### Cursor

**Settings:** `Cursor Settings > Features > MCP Servers > Add new MCP server`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### VS Code (GitHub Copilot)

**File:** `.vscode/mcp.json` (project) or user settings

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### Windsurf

**File:** `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### JetBrains AI Assistant

**Settings:** `Settings > Tools > AI Assistant > Model Context Protocol (MCP) > + Add`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### Gemini CLI

**File:** `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### Claude Code CLI

```bash
claude mcp add canon -- uvx mcp-canon
```

### Roo Code / Kilo Code

**File:** `.roo/mcp.json` or `.kilocode/mcp.json`

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["mcp-canon"]
    }
  }
}
```

### Augment Code

**File:** VS Code settings under `augment.advanced`

```json
{
  "augment.advanced": {
    "mcpServers": [
      {
        "name": "canon",
        "command": "uvx",
        "args": ["mcp-canon"]
      }
    ]
  }
}
```

### Warp

**Settings:** `Settings > AI > Manage MCP servers > + Add`

```json
{
  "canon": {
    "command": "uvx",
    "args": ["mcp-canon"],
    "env": {},
    "start_on_launch": true
  }
}
```

### OpenAI Codex CLI

**File:** `~/.codex/config.toml`

```toml
[mcp_servers.canon]
command = "uvx"
args = ["mcp-canon"]
```

### HTTP Server Connection

For clients supporting remote MCP servers (after running `canon serve`):

```json
{
  "mcpServers": {
    "canon": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Using pip instead of uvx

If you installed via pip instead of uvx:

```json
{
  "mcpServers": {
    "canon": {
      "command": "python",
      "args": ["-m", "mcp_canon"]
    }
  }
}
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CANON_DB_PATH` | Path to custom database | Bundled DB |
| `CANON_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `CANON_LOG_JSON` | Output logs in JSON format | false |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Writing Guides](docs/writing-guides.md) | How to write guides that index well — frontmatter schema, content structure best practices, and search optimization |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_best_practices` | Semantic search for best practices (within a guide if guide_id is provided) |
| `search_suitable_guides` | Find guides matching a task description |
| `read_full_guide` | Get complete guide content |

---

## CLI Commands

```bash
# Indexing
canon index --library ./library           # Index guides (creates new DB)
canon index --library ./lib --append      # Add to existing database
canon validate --library ./library        # Validate frontmatter

# Server
canon serve --port 8080                   # Start HTTP server (requires [http])

# Info
canon list                                # List indexed guides
canon info                                # Show database info
```

---

## Frontmatter Schema

Required fields in `INDEX.md`:

```yaml
---
name: guide-name              # Must match folder name
description: "Guide description for semantic search"
metadata:
  tags:                       # From controlled vocabulary
    - python
    - fastapi
  type: local                 # "local" for GUIDE.md, "link" for URL
  url: https://...            # Required if type: link
---
```

---

## License

MIT
