"""Tests for schema validation."""

import pytest
from pydantic import ValidationError

from mcp_canon.schemas.frontmatter import (
    GuideFrontmatter,
    GuideMetadata,
)


class TestGuideMetadata:
    """Tests for GuideMetadata validation."""

    def test_valid_local_metadata(self):
        """Test valid local type metadata."""
        metadata = GuideMetadata(
            tags=["python", "fastapi"],
            type="local",
        )
        assert metadata.type == "local"
        assert metadata.tags == ["python", "fastapi"]

    def test_valid_link_metadata(self):
        """Test valid link type metadata."""
        metadata = GuideMetadata(
            tags=["docker"],
            type="link",
            url="https://docs.docker.com/guide",
            format="html",
        )
        assert metadata.type == "link"
        assert metadata.url == "https://docs.docker.com/guide"

    def test_link_requires_url(self):
        """Test that link type requires URL."""
        with pytest.raises(ValueError, match="URL is required"):
            GuideMetadata(
                tags=["docker"],
                type="link",
                format="html",
            )

    def test_link_requires_format(self):
        """Test that link type requires format."""
        with pytest.raises(ValueError, match="Format is required"):
            GuideMetadata(
                tags=["docker"],
                type="link",
                url="https://example.com",
            )

    def test_arbitrary_tags_allowed(self):
        """Test that any domain tags are accepted."""
        metadata = GuideMetadata(
            tags=["python", "marketing-funnel", "video-editing"],
            type="local",
        )
        assert metadata.tags == ["python", "marketing-funnel", "video-editing"]

    def test_empty_tags_rejected(self):
        """Test that empty tags list is rejected."""
        with pytest.raises(ValidationError):
            GuideMetadata(
                tags=[],
                type="local",
            )


class TestGuideFrontmatter:
    """Tests for GuideFrontmatter validation."""

    def test_valid_frontmatter(self):
        """Test valid frontmatter."""
        fm = GuideFrontmatter(
            name="my-guide",
            description="A valid description that is at least 20 characters long",
            metadata=GuideMetadata(tags=["python"], type="local"),
        )
        assert fm.name == "my-guide"

    def test_invalid_name_format(self):
        """Test that non-kebab-case names are rejected."""
        with pytest.raises(ValidationError, match="Invalid name format"):
            GuideFrontmatter(
                name="MyGuide",  # Not kebab-case
                description="A valid description that is at least 20 characters long",
                metadata=GuideMetadata(tags=["python"], type="local"),
            )

    def test_description_too_short(self):
        """Test that short descriptions are rejected."""
        with pytest.raises(ValidationError):
            GuideFrontmatter(
                name="my-guide",
                description="Too short",
                metadata=GuideMetadata(tags=["python"], type="local"),
            )

    def test_description_too_long(self):
        """Test that long descriptions are rejected."""
        with pytest.raises(ValidationError):
            GuideFrontmatter(
                name="my-guide",
                description="x" * 501,
                metadata=GuideMetadata(tags=["python"], type="local"),
            )
