# mcp-canon

Universal MCP knowledge server for LLM agents, powered by local RAG.

Use Canon to provide domain-specific best practices and playbooks across software engineering,
marketing, video editing, and other knowledge areas.

Typical workflows:
- Find the most suitable guide for a task
- Retrieve concise best-practice snippets
- Read full guides for deeper execution context

---

## Quick Start

<details>
<summary><b>Install in Cursor</b></summary>

Go to: `Settings` -> `Cursor Settings` -> `MCP` -> `Add new global MCP server`

Pasting the following configuration into your Cursor `~/.cursor/mcp.json` file is the recommended approach. You may also install in a specific project by creating `.cursor/mcp.json` in your project folder. See [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol) for more info.

#### Cursor Local Connection

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
#### Cursor Local Connection With Custom Database

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

#### Cursor Remote Server Connection

```json
{
  "mcpServers": {
    "canon": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

</details>

<details>
<summary><b>Install in Claude Code</b></summary>

Run this command. See [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) for more info.

#### Claude Code Local Connection

```sh
claude mcp add --scope user canon -- uvx mcp-canon
```

#### Cursor Local Connection With Custom Database


```sh
claude mcp add --scope user -e CANON_DB_PATH=/path/to/my-db canon -- uvx mcp-canon
```

#### Claude Code Remote Server Connection

```sh
claude mcp add --scope user --transport http canon http://localhost:8080/mcp
```

> Remove `--scope user` to install for the current project only.

</details>

<details>
<summary><b>Install in Opencode</b></summary>

Add this to your Opencode configuration file. See [Opencode MCP docs](https://opencode.ai/docs/mcp-servers) for more info.


#### Opencode Local Connection

```json
{
  "mcp": {
    "canon": {
      "type": "local",
      "command": ["uvx", "mcp-canon"],
      "enabled": true
    }
  }
}
```

#### Opencode Local Connection With Custom Database

```json
{
  "mcp": {
    "canon": {
      "type": "local",
      "command": ["uvx", "mcp-canon"],
      "enabled": true,
      "environment": {
        "CANON_DB_PATH": "/path/to/my-db"
      }
    }
  }
}
```

#### Opencode Remote Server Connection

```json
"mcp": {
  "context7": {
    "type": "remote",
    "url": "http://localhost:8080/mcp",
    "enabled": true
  }
}
```

</details>

<details>
<summary><b>Install in Gemini CLI</b></summary>

Run this command. See [Gemini CLI MCP docs](https://geminicli.com/docs/tools/mcp-server/) for more
info.

#### Gemini CLI Local Connection

```sh
gemini mcp add --scope user canon uvx mcp-canon
```

#### Gemini CLI Local Connection With Custom Database

```sh
gemini mcp add --scope user -e CANON_DB_PATH=/path/to/my-db canon uvx mcp-canon
```

#### Gemini CLI Remote Server Connection

```sh
gemini mcp add --scope user --transport http canon http://localhost:8080/mcp
```

> Remove `--scope user` to install for the current project only.

</details>

<details>
<summary><b>Install in Google Antigravity</b></summary>

Go to the agent panel and open: `...` -> `MCP Servers` -> `Manage MCP Servers` -> `View raw config`.
Add this to your `mcp_config.json` file. See [Google Antigravity MCP docs](https://antigravity.google/docs/mcp#connecting-custom-mcp-servers) for more info.

#### Google Antigravity Local Connection

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

#### Google Antigravity Local Connection With Custom Database

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

</details>

---

## Create and index your own guides

Complete workflow from installation to running with your own domain guides.

### Step 1: Install with indexing support

```bash
pip install "mcp-canon[indexing]"
```

### Step 2: Create library structure

```
my-library/
├── engineering/
│   └── python-fastapi-guide/
│       ├── INDEX.md      # Required: metadata
│       └── GUIDE.md      # Content
├── marketing/
│   └── launch-playbook/
│       ├── INDEX.md
│       └── GUIDE.md
└── video-editing/
    └── shorts-workflow/
        └── INDEX.md      # Can reference external URL
```
### Step 3: [Create guides](docs/writing-guides.md)



### Step 4: Index your library

```bash
# Index to custom location
canon index --library ./my-library --output /path/to/my-db

# Validate frontmatter before indexing (optional)
canon validate --library ./my-library
```

## Running as HTTP server

For remote access or multi-client scenarios, run Canon as an HTTP server.
This is useful when multiple agents or teams share one cross-domain knowledge base.

### Step 1: Install with HTTP support

```bash
pip install "mcp-canon[http]"
```

### Step 2: Start the server

```bash
# Default port 8080
canon serve

# Custom port and host
canon serve --port 3000 --host 0.0.0.0

# With custom database
CANON_DB_PATH=/path/to/db canon serve --port 8080
```

### Step 3: Configure MCP client

```json
{
  "mcpServers": {
    "canon": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```


## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CANON_DB_PATH` | Path to custom database | Bundled DB |
| `CANON_EMBEDDING_MODEL` | Fastembed model name ([supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/)) | `nomic-ai/nomic-embed-text-v1.5-Q` |
| `CANON_EMBEDDING_DIM` | Embedding vector dimensions (must match model) | `768` |
| `CANON_FASTEMBED_THREADS` | ONNX runtime threads for FastEmbed (lower = less RAM, slower) | auto |
| `CANON_FASTEMBED_BATCH_SIZE` | Embedding batch size during indexing (lower = less RAM, slower) | `256` |
| `CANON_FASTEMBED_PARALLEL` | FastEmbed data-parallel workers (`>1` increases RAM usage) | disabled |
| `CANON_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `CANON_LOG_JSON` | Output logs in JSON format | false |

> **Note:** Changing `CANON_EMBEDDING_MODEL` or `CANON_EMBEDDING_DIM` requires a full reindex: `canon index --library ./library`

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_best_practices` | Semantic search for best practices in any domain (optionally scoped by guide_id) |
| `search_suitable_guides` | Find guides that match a task description across domains |
| `read_full_guide` | Get complete guide content for full context |

---

## CLI Commands

```bash
# Indexing
canon index --library ./library           # Index guides from any domain (creates new DB)
canon index --library ./lib --append      # Add to existing database
canon validate --library ./library        # Validate frontmatter

# Server
canon serve --port 8080                   # Start HTTP server (requires [http])

# Info
canon list                                # List indexed guides
canon info                                # Show database info
```

---

## License

MIT
