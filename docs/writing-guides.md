# Writing Guides for Canon

How to write guides that index well and deliver high-quality search results.

---

## Library Structure

Canon uses a two-level directory structure:

```
library/
├── <namespace>/              # Technology stack (e.g., python, kubernetes)
│   └── <guide-name>/        # Guide directory (kebab-case)
│       ├── INDEX.md          # Required: metadata (frontmatter)
│       └── GUIDE.md          # Required for local guides: content
└── <namespace>/
    └── <guide-name>/
        └── INDEX.md          # Can reference external URL instead
```

**Key rules:**
- `<namespace>` = top-level technology (e.g., `python`, `docker`, `kubernetes`)
- `<guide-name>` = kebab-case name matching the frontmatter `name` field
- Every guide **must** have an `INDEX.md` with valid frontmatter
- Local guides **must** have a `GUIDE.md` with the content

---

## INDEX.md — Frontmatter Schema

```yaml
---
name: django-security          # Must match directory name, kebab-case only
description: "Production-ready security patterns for Django applications including
  authentication, authorization, CSRF protection, and secrets management"
metadata:
  tags:
    - python
    - django
    - security
    - authentication
  type: local                  # "local" = GUIDE.md in same directory
---
```

### Field Reference

| Field | Rules | Impact |
|-------|-------|--------|
| `name` | Kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`), must match folder name | Guide ID = `namespace/name` |
| `description` | 20–500 characters | Reference info returned in search results and guide listings (not used for search ranking) |
| `tags` | ≥ 1 tag from [controlled vocabulary](#allowed-tags) | Namespace filtering |
| `type` | `local` or `link` | Determines content source |
| `url` | Required if `type: link` | External content URL |
| `format` | Required if `type: link` (`markdown`, `html`, `pdf`, `docx`) | Parser selection |

### What Actually Drives Search

Canon uses two separate mechanisms for search — neither relies on the `description` field:

1. **Guide-level search** (`search_suitable_guides`) — uses `summary_vector`, which is built from an **extractive summary**: the top ~10% most representative chunks selected by semantic centroid. This means your **guide content** (GUIDE.md) determines whether the guide appears in results.

2. **Chunk-level search** (`search_best_practices`) — uses hybrid vector+BM25 search across chunk content and heading paths.

The `description` field is **reference metadata only** — it's returned in search results and guide listings to help users understand what a guide covers, but it has zero effect on search ranking.

### Writing Good Descriptions

Even though `description` doesn't affect search ranking, it's still important — LLM agents read it to decide whether to open the full guide:

```yaml
# ✅ Helps agents decide if the guide is relevant
description: "Production-ready FastAPI patterns including project structure,
  dependency injection, async database access, and error handling"

# ❌ Too vague to be useful
description: "Best practices for web development"
```

---

## GUIDE.md — Content Structure

Canon's chunking engine splits content by **heading hierarchy**. Structure directly affects search precision.

### How Chunking Works

1. Content is split into **H2 sections**
2. Small H2 sections (< 5000 chars) → kept as a single chunk
3. Large H2 sections (≥ 5000 chars) → split further by H3 subsections
4. Each chunk stores its **heading** and **heading path** (e.g., `Project Structure > Directory Layout`)

### How Search Works

Canon uses **hybrid search** combining:
- **Vector search** — cosine similarity on `nomic-embed-text-v1.5` embeddings (1024 dimensions)
- **BM25 keyword search** — full-text search on chunk heading paths (full breadcrumb like `Authentication > JWT Token Setup`)
- **RRF reranking** — Reciprocal Rank Fusion merges both signals

The `heading_path` field (full heading breadcrumb) receives BM25 keyword boost. This means parent headings like `Authentication` contribute to ranking even for sub-chunks like `JWT Token Setup`.

### Best Practices

#### Use Clear, Searchable Headings

Headings are indexed for both vector and keyword search. Make them specific:

```markdown
<!-- ✅ Good: specific, searchable -->
## Password Hashing with bcrypt
## Database Connection Pooling
## JWT Token Refresh Flow

<!-- ❌ Bad: vague, generic -->
## Overview
## Details
## More Info
```

#### Structure with H2 → H3 Hierarchy

Use H2 for major topics and H3 for subtopics. This maps directly to Canon's chunking strategy:

```markdown
# FastAPI Security Guide        ← H1 (guide title, not chunked separately)

## Authentication                ← H2 → becomes chunk boundary
### JWT Token Setup              ← H3 → sub-chunk if H2 section is large
### OAuth2 Integration           ← H3
### Session Management           ← H3

## Authorization                 ← H2 → next chunk boundary
### Role-Based Access Control    ← H3
### Permission Decorators        ← H3
```

#### Keep H2 Sections Focused

Each H2 section should cover **one coherent topic**. When a user searches for "JWT authentication", the entire H2 section is returned as context — if it mixes unrelated topics, the result quality drops.

```markdown
<!-- ✅ Good: focused H2 -->
## Error Handling
All error handling patterns in one place.

<!-- ❌ Bad: mixed topics in one H2 -->
## Error Handling and Logging and Monitoring
Three different topics in one section.
```

#### Optimal Section Sizes

| Section Type | Recommended Size | Why |
|-------------|-----------------|-----|
| H2 section | 1000–5000 chars | Below 5000 stays as single chunk = complete context |
| H3 subsection | 500–2000 chars | When H2 is split, each H3 becomes a chunk |
| Total guide | 5000–50000 chars | Enough depth for real patterns |

Sections under 200 chars are too thin to embed well. Sections over 8000 chars risk exceeding LLM context windows.

#### Include Code Examples

Code examples dramatically improve search relevance — they contain natural keyword matches:

```markdown
## Database Connection Pooling

Use connection pooling to avoid exhausting database connections:

\```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)
\```
```

#### Use Descriptive Headings, Not Numbers

```markdown
<!-- ✅ Searchable -->
## Rate Limiting with Redis
## Graceful Shutdown Handling

<!-- ❌ Not searchable -->
## Step 1
## Pattern 3.2
```

---

## Allowed Tags

Tags must come from the controlled vocabulary. Using invalid tags will cause validation error `E006`.

| Category | Tags |
|----------|------|
| **Languages** | `python`, `go`, `typescript`, `javascript`, `rust`, `java` |
| **Web Frameworks** | `fastapi`, `django`, `flask`, `litestar`, `express`, `nextjs` |
| **DevOps** | `docker`, `dockerfile`, `kubernetes`, `helm`, `terraform`, `ansible`, `ci-cd`, `istio` |
| **Security** | `security`, `authentication`, `authorization`, `cryptography`, `secrets` |
| **Databases** | `postgresql`, `mysql`, `mongodb`, `redis`, `sqlite`, `sql` |
| **Architecture** | `api`, `rest`, `graphql`, `grpc`, `microservices`, `monolith`, `async` |
| **Testing** | `testing`, `unit-testing`, `integration-testing`, `e2e`, `mocking` |
| **Code Quality** | `style`, `linting`, `typing`, `documentation`, `logging`, `error-handling` |
| **Deployment** | `production`, `deployment`, `monitoring`, `performance`, `scaling`, `caching` |
| **ORM / Data** | `sqlalchemy`, `pydantic`, `alembic`, `orm` |
| **Web** | `web`, `http`, `websocket`, `cors`, `middleware`, `containerization` |

---

## Validation Errors

Run `canon validate --library ./library` before indexing. Reference of error codes:

| Code | Meaning |
|------|---------|
| `E001` | Invalid name format — must be kebab-case |
| `E002` | Name doesn't match directory name |
| `E003` | Description too short (< 20 chars) |
| `E004` | Description too long (> 500 chars) |
| `E005` | No tags provided |
| `E006` | Unknown tag — not in controlled vocabulary |
| `E007` | URL required for `type: link` |
| `E008` | Format required for `type: link` |
| `E010` | Unsupported format |

---

## Workflow

```bash
# 1. Create guide structure
mkdir -p library/python/my-guide

# 2. Write INDEX.md with frontmatter
# 3. Write GUIDE.md with content

# 4. Validate
canon validate --library ./library

# 5. Index
canon index --library ./library

# 6. Verify
canon list
canon info
```

---

## Complete Example

### `library/python/fastapi-security/INDEX.md`

```yaml
---
name: fastapi-security
description: "Security patterns for FastAPI applications including JWT authentication,
  OAuth2 flows, CORS configuration, rate limiting, and input validation with Pydantic"
metadata:
  tags:
    - python
    - fastapi
    - security
    - authentication
    - api
  type: local
---
```

### `library/python/fastapi-security/GUIDE.md`

```markdown
# FastAPI Security Guide

## Authentication

### JWT Token Setup

Configure JWT authentication with python-jose:

\```python
from jose import jwt
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
\```

### OAuth2 Password Flow

FastAPI has built-in OAuth2 support:

\```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
\```

## Input Validation

### Pydantic Models for Request Validation

Always validate user input with strict Pydantic models:

\```python
from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
\```

## Rate Limiting

### Redis-Based Rate Limiter

Implement sliding window rate limiting:

\```python
from fastapi import Request, HTTPException
import redis

r = redis.Redis()

async def rate_limit(request: Request, limit: int = 100):
    key = f"rate:{request.client.host}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, 60)
    if current > limit:
        raise HTTPException(429, "Rate limit exceeded")
\```
```
