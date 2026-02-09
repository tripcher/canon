"""Tests for schema validation."""

import pytest
from pydantic import ValidationError

from mcp_canon.schemas.frontmatter import (
    ALLOWED_TAGS,
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

    def test_invalid_tag(self):
        """Test that unknown tags are rejected."""
        with pytest.raises(ValidationError, match="Unknown tag"):
            GuideMetadata(
                tags=["not-a-valid-tag"],
                type="local",
            )

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


class TestAllowedTags:
    """Tests for controlled vocabulary."""

    def test_common_tags_exist(self):
        """Test that common tags are in the vocabulary."""
        common_tags = [
            "python",
            "go",
            "docker",
            "kubernetes",
            "fastapi",
            "django",
            "security",
            "api",
        ]
        for tag in common_tags:
            assert tag in ALLOWED_TAGS, f"Tag '{tag}' should be allowed"

    def test_synonyms_not_allowed(self):
        """Test that common synonyms are not in vocabulary."""
        synonyms = ["py", "k8s", "js", "ts", "auth"]
        for tag in synonyms:
            assert tag not in ALLOWED_TAGS, f"Synonym '{tag}' should not be allowed"
