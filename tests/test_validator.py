"""Tests for frontmatter validation."""

import tempfile
from pathlib import Path

from mcp_canon.ingestion.validator import (
    parse_frontmatter,
    validate_frontmatter,
)


class TestParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        content = """---
name: my-guide
description: A test description
metadata:
  tags:
    - python
  type: local
---

# Guide Content
"""
        result = parse_frontmatter(content)
        assert result is not None
        assert result["name"] == "my-guide"

    def test_no_frontmatter(self):
        """Test content without frontmatter."""
        content = "# Just Markdown"
        result = parse_frontmatter(content)
        assert result is None

    def test_invalid_yaml(self):
        """Test parsing invalid YAML."""
        content = """---
name: [invalid yaml
---"""
        result = parse_frontmatter(content)
        assert result is None


class TestValidateFrontmatter:
    """Tests for frontmatter validation."""

    def test_valid_local_guide(self):
        """Test validation of valid local guide."""
        content = """---
name: my-guide
description: "A valid description that is long enough for validation"
metadata:
  tags:
    - python
    - fastapi
  type: local
---
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            result = validate_frontmatter(Path(f.name), "my-guide")

        assert result.success
        assert result.frontmatter is not None
        assert result.frontmatter.name == "my-guide"

    def test_name_mismatch_e002(self):
        """Test E002 error for name mismatch."""
        content = """---
name: different-name
description: "A valid description that is long enough"
metadata:
  tags:
    - python
  type: local
---
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            result = validate_frontmatter(Path(f.name), "expected-name")

        assert not result.success
        assert result.error_code == "E002"

    def test_invalid_name_format_e001(self):
        """Test E001 error for invalid name format."""
        content = """---
name: InvalidName
description: "A valid description that is long enough"
metadata:
  tags:
    - python
  type: local
---
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            result = validate_frontmatter(Path(f.name))

        assert not result.success
        assert result.error_code == "E001"
