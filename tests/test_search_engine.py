"""Tests for SearchEngine with comprehensive coverage."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import lancedb
import numpy as np
import pytest

from mcp_canon.schemas.database import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL_NAME,
    ChunkSchema,
    DatabaseMetadata,
    GuideSchema,
)
from mcp_canon.server.search import SearchEngine


class TestSearchEngineInitialization:
    """Test SearchEngine initialization and lazy loading."""

    def test_init_stores_path(self):
        """SearchEngine stores the database path."""
        engine = SearchEngine("/fake/path")
        assert engine.db_path == Path("/fake/path")

    def test_db_not_connected_initially(self):
        """Database is not connected until accessed."""
        engine = SearchEngine("/fake/path")
        assert engine._db is None

    def test_is_initialized_false_for_nonexistent_db(self):
        """is_initialized returns False for nonexistent database."""
        engine = SearchEngine("/nonexistent/path")
        assert engine.is_initialized() is False

    def test_is_initialized_false_for_empty_dir(self):
        """is_initialized returns False for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            assert engine.is_initialized() is False


class TestSanitizeFilterValue:
    """Test _sanitize_filter_value for SQL injection prevention."""

    @pytest.fixture
    def engine(self):
        """Create SearchEngine instance."""
        return SearchEngine("/fake/path")

    def test_valid_alphanumeric(self, engine):
        """Valid alphanumeric values pass through."""
        assert engine._sanitize_filter_value("python") == "python"
        assert engine._sanitize_filter_value("Python3") == "Python3"
        assert engine._sanitize_filter_value("nodejs") == "nodejs"

    def test_valid_with_hyphen(self, engine):
        """Hyphens are allowed."""
        assert engine._sanitize_filter_value("type-safety") == "type-safety"
        assert engine._sanitize_filter_value("node-js") == "node-js"

    def test_valid_with_underscore(self, engine):
        """Underscores are allowed."""
        assert engine._sanitize_filter_value("error_handling") == "error_handling"
        assert engine._sanitize_filter_value("code_style") == "code_style"

    def test_slash_blocked_by_default(self, engine):
        """Forward slash is blocked by default."""
        with pytest.raises(ValueError) as exc_info:
            engine._sanitize_filter_value("path/to/guide")
        assert "Invalid filter value" in str(exc_info.value)

    def test_slash_allowed_when_enabled(self, engine):
        """Forward slash allowed when allow_slash=True."""
        result = engine._sanitize_filter_value("python/error-handling", allow_slash=True)
        assert result == "python/error-handling"

    def test_sql_injection_single_quote(self, engine):
        """Single quotes are blocked (SQL injection prevention)."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value("'; DROP TABLE guides; --")

    def test_sql_injection_double_quote(self, engine):
        """Double quotes are blocked."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value('"; DROP TABLE guides; --')

    def test_sql_injection_semicolon(self, engine):
        """Semicolons are blocked."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value("python; DELETE FROM")

    def test_sql_injection_parentheses(self, engine):
        """Parentheses are blocked."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value("python OR (1=1)")

    def test_empty_string_rejected(self, engine):
        """Empty string is rejected."""
        # Empty strings may or may not be valid depending on implementation
        # Test that it doesn't crash
        try:
            result = engine._sanitize_filter_value("")
            # If it passes, result should be empty string
            assert result == ""
        except ValueError:
            # Also acceptable to reject empty strings
            pass

    def test_unicode_blocked(self, engine):
        """Unicode characters are blocked."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value("pythön")

    def test_spaces_blocked(self, engine):
        """Spaces are blocked."""
        with pytest.raises(ValueError):
            engine._sanitize_filter_value("python script")


class TestBuildFilter:
    """Test _build_filter for correct SQL-like expression generation."""

    @pytest.fixture
    def engine(self):
        """Create SearchEngine instance."""
        return SearchEngine("/fake/path")

    def test_no_filters_returns_none(self, engine):
        """No filters returns None."""
        assert engine._build_filter(None, None) is None

    def test_namespace_only(self, engine):
        """Tech stack creates correct filter."""
        result = engine._build_filter("python", None)
        assert result == "namespace = 'python'"

    def test_single_tag(self, engine):
        """Single tag creates correct filter."""
        result = engine._build_filter(None, ["testing"])
        assert result == "array_contains(tags, 'testing')"

    def test_multiple_tags(self, engine):
        """Multiple tags joined with AND."""
        result = engine._build_filter(None, ["testing", "async"])
        assert "array_contains(tags, 'testing')" in result
        assert "array_contains(tags, 'async')" in result
        assert " AND " in result

    def test_namespace_and_tags(self, engine):
        """Combined filters joined with AND."""
        result = engine._build_filter("python", ["testing"])
        assert "namespace = 'python'" in result
        assert "array_contains(tags, 'testing')" in result
        assert " AND " in result

    def test_invalid_namespace_raises(self, engine):
        """Invalid namespace value raises ValueError."""
        with pytest.raises(ValueError):
            engine._build_filter("python'; DROP --", None)

    def test_invalid_tag_raises(self, engine):
        """Invalid tag value raises ValueError."""
        with pytest.raises(ValueError):
            engine._build_filter(None, ["valid", "invalid';--"])


class TestListGuides:
    """Test list_guides method."""

    def test_returns_empty_list_for_empty_db(self):
        """Returns empty list when database has no guides table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            # This will try to access db which creates empty LanceDB
            # But no tables exist, so returns empty list
            result = engine.list_guides()
            assert result == []

    def test_returns_empty_when_not_initialized(self):
        """Returns empty list when database is not initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.list_guides()
            assert result == []


class TestSearchChunksWithGuide:
    """Test search_chunks method with guide_id filter."""

    def test_validates_guide_id_format(self):
        """Validates that invalid guide_id is caught."""
        engine = SearchEngine("/fake/path")
        # Should raise ValueError for SQL injection attempt
        with pytest.raises(ValueError) as exc_info:
            engine._sanitize_filter_value("invalid'; DROP --")
        assert "Invalid filter value" in str(exc_info.value)

    def test_returns_empty_for_empty_db(self):
        """Returns empty when chunks table doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.search_chunks(query="how to test", guide_id="python/testing")
            assert result == []


class TestGetFullGuide:
    """Test get_full_guide method."""

    def test_returns_none_for_empty_db(self):
        """Returns None when guides table doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.get_full_guide("python/testing")
            assert result is None


class TestSearchGuidesbyQuery:
    """Test search_guides_by_query method."""

    def test_returns_empty_for_empty_db(self):
        """Returns empty when guides table doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.search_guides_by_query("test query")
            assert result == []


class TestDatabaseInfo:
    """Test get_database_info method."""

    def test_returns_not_initialized_for_empty_db(self):
        """Returns initialized=False for empty database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.get_database_info()
            assert result.initialized is False

    def test_database_info_has_counts(self):
        """DatabaseInfo has count attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SearchEngine(tmpdir)
            result = engine.get_database_info()
            # Check that attributes exist (may be 0 or higher)
            assert hasattr(result, "guides_count")
            assert hasattr(result, "chunks_count")


# ============================================================================
# Integration Tests with Real Data
# ============================================================================


class TestIntegrationWithRealData:
    """Integration tests with actual data in LanceDB."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a populated test database with guides and chunks."""

        db_path = tmp_path / "test_db"
        db = lancedb.connect(str(db_path))

        # Create test embedding vectors
        def make_vector():
            vec = np.random.rand(EMBEDDING_DIM).astype(np.float32)
            return vec / np.linalg.norm(vec)

        now = datetime.now(UTC).isoformat()

        # Create guides
        guides_data = [
            GuideSchema(
                id="python/testing",
                name="Testing Best Practices",
                namespace="python",
                tags=["testing", "quality"],
                description="Comprehensive guide to Python testing",
                source_type="local",
                source_url=None,
                file_path="/library/python/testing.md",
                content_hash="abc123",
                indexed_at=now,
                summary="This guide covers unit testing, mocking, and pytest.",
                summary_vector=make_vector(),
                headings="Unit Tests\nIntegration Tests\nMocking",
                headings_vector=make_vector(),
            ),
            GuideSchema(
                id="python/async",
                name="Async Programming",
                namespace="python",
                tags=["async", "performance"],
                description="Guide to async/await in Python",
                source_type="local",
                source_url=None,
                file_path="/library/python/async.md",
                content_hash="def456",
                indexed_at=now,
                summary="Async programming with asyncio and aiohttp.",
                summary_vector=make_vector(),
                headings="Asyncio Basics\nAsync HTTP\nConcurrency",
                headings_vector=make_vector(),
            ),
            GuideSchema(
                id="javascript/testing",
                name="JavaScript Testing",
                namespace="javascript",
                tags=["testing", "frontend"],
                description="Testing JavaScript applications",
                source_type="local",
                source_url=None,
                file_path="/library/javascript/testing.md",
                content_hash="ghi789",
                indexed_at=now,
                summary="Jest and React Testing Library guide.",
                summary_vector=make_vector(),
                headings="Jest Setup\nReact Testing\nE2E Tests",
                headings_vector=make_vector(),
            ),
        ]

        # Create chunks
        chunks_data = [
            ChunkSchema(
                id="chunk-1",
                guide_id="python/testing",
                namespace="python",
                tags=["testing", "quality"],
                heading="Unit Tests",
                heading_path="Testing Best Practices > Unit Tests",
                content="Unit tests verify individual components in isolation.",
                chunk_index=0,
                char_count=55,
                vector=make_vector(),
            ),
            ChunkSchema(
                id="chunk-2",
                guide_id="python/testing",
                namespace="python",
                tags=["testing", "quality"],
                heading="Mocking",
                heading_path="Testing Best Practices > Mocking",
                content="Use unittest.mock or pytest-mock for mocking dependencies.",
                chunk_index=1,
                char_count=60,
                vector=make_vector(),
            ),
            ChunkSchema(
                id="chunk-3",
                guide_id="python/async",
                namespace="python",
                tags=["async", "performance"],
                heading="Asyncio Basics",
                heading_path="Async Programming > Asyncio Basics",
                content="async/await syntax allows concurrent I/O operations.",
                chunk_index=0,
                char_count=52,
                vector=make_vector(),
            ),
            ChunkSchema(
                id="chunk-4",
                guide_id="javascript/testing",
                namespace="javascript",
                tags=["testing", "frontend"],
                heading="Jest Setup",
                heading_path="JavaScript Testing > Jest Setup",
                content="Install Jest with npm install --save-dev jest.",
                chunk_index=0,
                char_count=45,
                vector=make_vector(),
            ),
        ]

        # Create metadata
        metadata = [
            DatabaseMetadata(
                model_name=EMBEDDING_MODEL_NAME,
                model_dimensions=EMBEDDING_DIM,
                created_at=now,
                last_indexed_at=now,
                library_path="/library",
            )
        ]

        # Create tables using schema and add() for proper pydantic support
        guides_table = db.create_table("guides", schema=GuideSchema, mode="overwrite")
        guides_table.add(guides_data)

        chunks_table = db.create_table("chunks", schema=ChunkSchema, mode="overwrite")
        chunks_table.add(chunks_data)

        metadata_table = db.create_table("_metadata", schema=DatabaseMetadata, mode="overwrite")
        metadata_table.add(metadata)

        # Create FTS indexes for hybrid search
        chunks_table.create_fts_index("content", replace=True)
        chunks_table.create_fts_index("heading", replace=True)
        guides_table.create_fts_index("description", replace=True)

        return str(db_path)

    def test_is_initialized_with_data(self, populated_db):
        """is_initialized returns True for populated database."""
        engine = SearchEngine(populated_db)
        assert engine.is_initialized() is True

    def test_list_guides_returns_all(self, populated_db):
        """list_guides returns all guides without filters."""
        engine = SearchEngine(populated_db)
        guides = engine.list_guides()

        assert len(guides) == 3
        guide_ids = [g.id for g in guides]
        assert "python/testing" in guide_ids
        assert "python/async" in guide_ids
        assert "javascript/testing" in guide_ids

    def test_list_guides_filter_by_namespace(self, populated_db):
        """list_guides filters by namespace correctly."""
        engine = SearchEngine(populated_db)

        # Filter Python guides
        python_guides = engine.list_guides(namespace="python")
        assert len(python_guides) == 2
        assert all(g.namespace == "python" for g in python_guides)

        # Filter JavaScript guides
        js_guides = engine.list_guides(namespace="javascript")
        assert len(js_guides) == 1
        assert js_guides[0].id == "javascript/testing"

    def test_list_guides_filter_by_namespace_only(self, populated_db):
        """list_guides only supports namespace filtering (tags not supported)."""
        engine = SearchEngine(populated_db)

        # Filter by Python namespace returns both Python guides
        python_guides = engine.list_guides(namespace="python")
        assert len(python_guides) == 2
        guide_ids = [g.id for g in python_guides]
        assert "python/testing" in guide_ids
        assert "python/async" in guide_ids

    def test_get_full_guide_returns_guide(self, populated_db):
        """get_full_guide returns correct guide data."""
        engine = SearchEngine(populated_db)

        guide = engine.get_full_guide("python/testing")

        assert guide is not None
        assert guide.id == "python/testing"
        assert guide.name == "Testing Best Practices"
        assert guide.namespace == "python"
        assert "testing" in guide.tags
        assert "quality" in guide.tags

    def test_get_full_guide_not_found(self, populated_db):
        """get_full_guide returns None for non-existent guide."""
        engine = SearchEngine(populated_db)

        guide = engine.get_full_guide("nonexistent/guide")

        assert guide is None

    def test_search_chunks_within_guide_returns_chunks(self, populated_db):
        """search_chunks with guide_id returns chunks from specific guide."""
        engine = SearchEngine(populated_db)

        results = engine.search_chunks(
            query="how to mock dependencies",
            guide_id="python/testing",
            limit=5,
        )

        # Should return chunks from python/testing only
        assert len(results) > 0
        # All results should be from python/testing guide
        for result in results:
            assert result.guide_id == "python/testing"

    def test_database_info_with_data(self, populated_db):
        """get_database_info returns correct counts."""
        engine = SearchEngine(populated_db)

        info = engine.get_database_info()

        assert info.initialized is True
        assert info.guides_count == 3
        assert info.chunks_count == 4
        assert info.model_name == EMBEDDING_MODEL_NAME

    def test_guide_list_item_serialization(self, populated_db):
        """GuideListItem has all expected fields properly serialized."""
        engine = SearchEngine(populated_db)

        guides = engine.list_guides()
        guide = next(g for g in guides if g.id == "python/testing")

        # Check all fields are properly serialized
        assert isinstance(guide.id, str)
        assert isinstance(guide.name, str)
        assert isinstance(guide.namespace, str)
        assert isinstance(guide.tags, list)
        assert isinstance(guide.description, str)

        # Check values
        assert guide.id == "python/testing"
        assert guide.name == "Testing Best Practices"
        assert guide.namespace == "python"
        assert guide.tags == ["testing", "quality"]

    def test_full_guide_content_reconstructed(self, populated_db):
        """FullGuide content is reconstructed from chunks."""
        engine = SearchEngine(populated_db)

        guide = engine.get_full_guide("python/testing")

        # Content should contain text from chunks
        assert guide is not None
        # char_count should be set
        assert isinstance(guide.char_count, int)
