"""Frontmatter validation schemas for INDEX.md files."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Controlled vocabulary from DATA_TAXONOMY.md
ALLOWED_TAGS: set[str] = {
    # Languages
    "python",
    "go",
    "typescript",
    "javascript",
    "rust",
    "java",
    # Web frameworks
    "fastapi",
    "django",
    "flask",
    "litestar",
    "express",
    "nextjs",
    # DevOps
    "docker",
    "dockerfile",
    "kubernetes",
    "helm",
    "terraform",
    "ansible",
    "ci-cd",
    "istio",
    # Security
    "security",
    "authentication",
    "authorization",
    "cryptography",
    "secrets",
    # Databases
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "sqlite",
    "sql",
    # Architecture
    "api",
    "rest",
    "graphql",
    "grpc",
    "microservices",
    "monolith",
    "async",
    # Testing
    "testing",
    "unit-testing",
    "integration-testing",
    "e2e",
    "mocking",
    # Code quality
    "style",
    "linting",
    "typing",
    "documentation",
    "logging",
    "error-handling",
    # Deployment
    "production",
    "deployment",
    "monitoring",
    "performance",
    "scaling",
    "caching",
    # ORM / Data layer
    "sqlalchemy",
    "pydantic",
    "alembic",
    "orm",
    # Web
    "web",
    "http",
    "websocket",
    "cors",
    "middleware",
    "containerization",
}

# Kebab-case pattern
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class GuideMetadata(BaseModel):
    """Metadata section of the frontmatter."""

    tags: list[str] = Field(..., min_length=1, description="List of tags for filtering")
    type: Literal["local", "link"] = Field(..., description="Source type")
    url: str | None = Field(None, description="URL for external sources (required if type=link)")
    format: Literal["markdown", "html", "pdf", "docx"] | None = Field(
        None, description="Format of external document (required if type=link)"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate that all tags are from controlled vocabulary."""
        invalid_tags = [tag for tag in v if tag not in ALLOWED_TAGS]
        if invalid_tags:
            raise ValueError(
                f"Unknown tags: {invalid_tags}. See DATA_TAXONOMY.md for allowed tags."
            )
        return v

    def model_post_init(self, __context: object) -> None:
        """Validate that url and format are present if type is link."""
        if self.type == "link":
            if not self.url:
                raise ValueError("URL is required for type: link")
            if not self.format:
                raise ValueError("Format is required for type: link")


class GuideFrontmatter(BaseModel):
    """Complete frontmatter schema for INDEX.md files."""

    name: str = Field(..., description="Guide name in kebab-case")
    description: str = Field(
        ..., min_length=20, max_length=500, description="Guide description for semantic search"
    )
    metadata: GuideMetadata

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is in kebab-case format."""
        if not KEBAB_CASE_PATTERN.match(v):
            raise ValueError(f"Invalid name format: '{v}'. Expected kebab-case.")
        return v


class ValidationError(BaseModel):
    """Validation error with code and message."""

    code: str
    message: str
    file_path: str | None = None


# Error codes mapping (from DATA_TAXONOMY.md)
ERROR_CODES = {
    "E001": "Invalid name format. Expected kebab-case.",
    "E002": "Name mismatch. 'name' field must match directory name.",
    "E003": "Description too short. Minimum 20 characters.",
    "E004": "Description too long. Maximum 500 characters.",
    "E005": "At least one tag is required.",
    "E006": "Unknown tag: '{tag}'. See DATA_TAXONOMY.md.",
    "E007": "URL is required for type: link.",
    "E008": "Format is required for type: link.",
    "E009": "Invalid URL format.",
    "E010": "Unsupported format: '{format}'.",
}
