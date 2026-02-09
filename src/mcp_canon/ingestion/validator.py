"""Frontmatter parsing and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError as PydanticValidationError

from mcp_canon.schemas.frontmatter import KEBAB_CASE_PATTERN, GuideFrontmatter


@dataclass
class ValidationResult:
    """Result of frontmatter validation."""

    success: bool
    frontmatter: GuideFrontmatter | None = None
    error_code: str | None = None
    error_message: str | None = None
    file_path: str | None = None


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Markdown content starting with ---

    Returns:
        Parsed YAML dict or None if no frontmatter found
    """
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])  # type: ignore[no-any-return]
    except yaml.YAMLError:
        return None


def validate_frontmatter(
    file_path: Path,
    directory_name: str | None = None,
) -> ValidationResult:
    """
    Validate INDEX.md frontmatter against schema.

    Args:
        file_path: Path to INDEX.md file
        directory_name: Expected directory name (for E002 check)

    Returns:
        ValidationResult with success status and parsed frontmatter or error
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        return ValidationResult(
            success=False,
            error_code="E000",
            error_message=f"Failed to read file: {e}",
            file_path=str(file_path),
        )

    # Parse YAML frontmatter
    raw_frontmatter = parse_frontmatter(content)
    if raw_frontmatter is None:
        return ValidationResult(
            success=False,
            error_code="E000",
            error_message="No valid YAML frontmatter found",
            file_path=str(file_path),
        )

    # Validate name format (E001)
    name = raw_frontmatter.get("name", "")
    if not KEBAB_CASE_PATTERN.match(name):
        return ValidationResult(
            success=False,
            error_code="E001",
            error_message=f"Invalid name format: '{name}'. Expected kebab-case.",
            file_path=str(file_path),
        )

    # Check name matches directory (E002)
    if directory_name is not None and name != directory_name:
        return ValidationResult(
            success=False,
            error_code="E002",
            error_message=f"Name mismatch. 'name' field '{name}' must match directory name '{directory_name}'.",
            file_path=str(file_path),
        )

    # Validate against Pydantic schema
    try:
        frontmatter = GuideFrontmatter(**raw_frontmatter)
        return ValidationResult(success=True, frontmatter=frontmatter)
    except PydanticValidationError as e:
        # Map Pydantic errors to our error codes
        first_error = e.errors()[0]
        loc = first_error.get("loc", ())
        msg = first_error.get("msg", "")

        error_code = "E000"
        error_message = msg

        # Map specific errors
        if "description" in loc:
            if "at least 20" in msg.lower() or "too short" in msg.lower():
                error_code = "E003"
                error_message = "Description too short. Minimum 20 characters."
            elif "at most 500" in msg.lower() or "too long" in msg.lower():
                error_code = "E004"
                error_message = "Description too long. Maximum 500 characters."
        elif "tags" in loc:
            if "at least 1" in msg.lower() or "empty" in msg.lower():
                error_code = "E005"
                error_message = "At least one tag is required."
            elif "Unknown tag" in msg:
                error_code = "E006"
                error_message = msg
        elif "url" in loc and "required" in msg.lower():
            error_code = "E007"
            error_message = "URL is required for type: link."
        elif "format" in loc:
            if "required" in msg.lower():
                error_code = "E008"
                error_message = "Format is required for type: link."
            elif "invalid" in msg.lower() or "unexpected" in msg.lower():
                error_code = "E010"
                error_message = f"Unsupported format. {msg}"

        return ValidationResult(
            success=False,
            error_code=error_code,
            error_message=error_message,
            file_path=str(file_path),
        )
