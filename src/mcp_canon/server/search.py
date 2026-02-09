"""Vector search engine for querying LanceDB using Pydantic models.

Uses LanceDB native vector search with bge-m3 embeddings.
"""

import re
from pathlib import Path
from typing import Any

import lancedb
from lancedb.embeddings import get_registry
from lancedb.rerankers import RRFReranker

from mcp_canon.logging import get_logger
from mcp_canon.schemas.database import (
    EMBEDDING_MODEL_NAME,
    ChunkSchema,
    DatabaseMetadata,
)
from mcp_canon.schemas.search import (
    ChunkSearchResult,
    DatabaseInfo,
    FullGuide,
    GuideListItem,
    GuideSearchResult,
)

logger = get_logger(__name__)


class SearchEngine:
    """Search engine for querying the vector database with native hybrid search."""

    def __init__(self, db_path: str | Path):
        """
        Initialize search engine.

        Args:
            db_path: Path to LanceDB database
        """
        self.db_path = Path(db_path)
        self._db: lancedb.DBConnection | None = None
        self._embedding_func: Any | None = None

    @property
    def db(self) -> lancedb.DBConnection:
        """Lazy-connect to database."""
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _embed_query(self, query: str) -> list[float]:
        """Embed a query string using the same model as ingestion."""
        if self._embedding_func is None:
            self._embedding_func = (
                get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)
            )
        vectors = self._embedding_func.compute_query_embeddings(query)
        return vectors[0]  # type: ignore[no-any-return]

    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self.db_path.exists() and "guides" in self.db.list_tables().tables

    def list_guides(
        self,
        namespace: str | None = None,
    ) -> list[GuideListItem]:
        """
        List all guides with optional namespace filtering.

        Args:
            namespace: Filter by technology stack

        Returns:
            List of guide metadata
        """
        if "guides" not in self.db.list_tables().tables:
            return []

        guides_table = self.db.open_table("guides")

        # Build filter for namespace only
        filter_expr = None
        if namespace:
            safe_tech = self._sanitize_filter_value(namespace)
            filter_expr = f"namespace = '{safe_tech}'"

        query = guides_table.search()
        if filter_expr:
            query = query.where(filter_expr)

        df = query.select(["id", "name", "namespace", "tags", "description"]).to_pandas()

        return [
            GuideListItem(
                id=row["id"],
                name=row["name"],
                namespace=row["namespace"],
                tags=row["tags"],
                description=row["description"],
            )
            for _, row in df.iterrows()
        ]

    def search_chunks(
        self,
        query: str,
        guide_id: str | None = None,
        namespace: str | None = None,
        limit: int = 5,
    ) -> list[ChunkSearchResult]:
        """
        Hybrid search across chunks with guide relevance filtering.

        First checks if any guides are semantically relevant to the query.
        If no relevant guides found, returns empty result (prevents returning
        irrelevant chunks for queries like 'django' when only Istio exists).

        Args:
            query: Search query
            guide_id: Optional guide ID to search within a specific guide
            namespace: Filter by technology stack
            limit: Maximum results

        Returns:
            List of matching chunks, empty if query is irrelevant to all guides
        """
        if "chunks" not in self.db.list_tables().tables:
            return []

        # Skip relevance check if searching within a specific guide
        if not guide_id:
            # Pre-check: are there any relevant guides for this query?
            relevant_guides = self.search_guides_by_query(
                query=query,
                namespace=namespace,
                limit=3,
            )
            if not relevant_guides:
                return []  # No relevant guides → no relevant chunks

            # Get relevance scores for guide-chunk mapping
            guide_scores = {g.id: g.relevance_score for g in relevant_guides}
        else:
            guide_scores = {}

        chunks_table = self.db.open_table("chunks")

        # Build filter expression
        filters = []
        if guide_id:
            safe_guide_id = self._sanitize_filter_value(guide_id, allow_slash=True)
            filters.append(f"guide_id = '{safe_guide_id}'")
        if namespace:
            safe_tech = self._sanitize_filter_value(namespace)
            filters.append(f"namespace = '{safe_tech}'")

        filter_expr = " AND ".join(filters) if filters else None

        # Hybrid search: cosine similarity + BM25 on heading
        search = (
            chunks_table.search(
                query,
                query_type="hybrid",
                vector_column_name="vector",
                fts_columns=["heading_path"],  # FTS only on heading for keyword boost
            )
            .distance_type("cosine")
            .rerank(RRFReranker())
            .limit(limit)
        )

        if filter_expr:
            search = search.where(filter_expr, prefilter=True)

        df = search.to_pandas()

        # Use guide's relevance score for chunk score (from summary_vector similarity)
        return [
            ChunkSearchResult(
                guide_id=row["guide_id"],
                guide_name=row["guide_id"].split("/")[-1],
                heading=row["heading"],
                heading_path=row["heading_path"],
                content=row["content"],
                relevance_score=guide_scores.get(row["guide_id"], 0.5),
                char_count=row["char_count"],
            )
            for _, row in df.iterrows()
        ]

    def search_guides_by_query(
        self,
        query: str,
        namespace: str | None = None,
        limit: int = 3,
        min_similarity: float = 0.7,
    ) -> list[GuideSearchResult]:
        """
        Vector search across guides using cosine similarity with threshold.

        Returns only guides where the query is semantically similar to the guide's
        summary. Irrelevant queries (e.g., 'react hooks' when only Istio exists)
        will return empty results.

        Args:
            query: Search query
            namespace: Filter by technology stack
            limit: Maximum results
            min_similarity: Minimum cosine similarity (0-1, higher = more similar).

        Returns:
            List of matching guides, empty if no relevant guides found
        """
        if "guides" not in self.db.list_tables().tables:
            return []

        guides_table = self.db.open_table("guides")

        # Build filter for namespace only
        filter_expr = None
        if namespace:
            safe_tech = self._sanitize_filter_value(namespace)
            filter_expr = f"namespace = '{safe_tech}'"

        # Embed query manually (guides table has no persisted embedding function)
        query_vector = self._embed_query(query)

        # Vector search with cosine similarity
        search = (
            guides_table.search(
                query_vector,
                query_type="vector",
                vector_column_name="summary_vector",
            )
            .distance_type("cosine")
            .limit(limit)
        )

        if filter_expr:
            search = search.where(filter_expr, prefilter=True)

        df = search.to_pandas()

        # Cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: similarity = 1 - distance/2
        # Filter by minimum similarity threshold
        df["similarity"] = 1 - df["_distance"] / 2
        df = df[df["similarity"] >= min_similarity]

        if len(df) == 0:
            return []

        return [
            GuideSearchResult(
                id=row["id"],
                name=row["name"],
                namespace=row["namespace"],
                tags=row["tags"],
                description=row["description"],
                relevance_score=round(row["similarity"], 2),
            )
            for _, row in df.iterrows()
        ]

    def get_full_guide(self, guide_id: str) -> FullGuide | None:
        """
        Get full guide content.

        Args:
            guide_id: ID of the guide

        Returns:
            Full guide or None if not found
        """
        if "guides" not in self.db.list_tables().tables:
            return None

        safe_guide_id = self._sanitize_filter_value(guide_id, allow_slash=True)

        guides_table = self.db.open_table("guides")
        df = (
            guides_table.search()
            .where(f"id = '{safe_guide_id}'")
            .limit(1)
            .select(["id", "name", "namespace", "tags", "description"])
            .to_pandas()
        )

        if len(df) == 0:
            return None

        row = df.iloc[0]
        content = self._get_guide_content(guide_id)

        return FullGuide(
            id=row["id"],
            name=row["name"],
            namespace=row["namespace"],
            tags=row["tags"],
            description=row["description"],
            content=content,
            char_count=len(content),
        )

    def _get_guide_content(self, guide_id: str) -> str:
        """Reconstruct guide content from chunks."""
        if "chunks" not in self.db.list_tables().tables:
            return ""

        safe_guide_id = self._sanitize_filter_value(guide_id, allow_slash=True)

        chunks_table = self.db.open_table("chunks")
        chunks = (
            chunks_table.search().where(f"guide_id = '{safe_guide_id}'").to_pydantic(ChunkSchema)
        )

        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)
        return "\n\n".join(c.content for c in sorted_chunks)

    def _sanitize_filter_value(self, value: str, allow_slash: bool = False) -> str:
        """
        Sanitize value for safe use in LanceDB filter expressions.

        Args:
            value: User-provided value to sanitize
            allow_slash: Whether to allow forward slash

        Returns:
            Sanitized value

        Raises:
            ValueError: If value contains disallowed characters
        """
        pattern = r"^[a-zA-Z0-9_-]+$" if not allow_slash else r"^[a-zA-Z0-9_/-]+$"
        if not re.match(pattern, value):
            raise ValueError(
                f"Invalid filter value: '{value}'. "
                f"Only alphanumeric characters, hyphens, and underscores are allowed."
            )
        return value

    def _build_filter(
        self,
        namespace: str | None,
        tags: list[str] | None,
    ) -> str | None:
        """
        Build LanceDB filter expression.

        Args:
            namespace: Technology stack filter
            tags: Tags filter

        Returns:
            SQL-like filter expression or None
        """
        conditions = []

        if namespace:
            safe_tech = self._sanitize_filter_value(namespace)
            conditions.append(f"namespace = '{safe_tech}'")

        if tags:
            for tag in tags:
                safe_tag = self._sanitize_filter_value(tag)
                conditions.append(f"array_contains(tags, '{safe_tag}')")

        if conditions:
            return " AND ".join(conditions)
        return None

    def get_database_info(self) -> DatabaseInfo:
        """Get database statistics."""
        info = DatabaseInfo(
            db_path=str(self.db_path),
            initialized=self.is_initialized(),
            guides_count=0,
            chunks_count=0,
            model_name=EMBEDDING_MODEL_NAME,
            last_indexed_at=None,
        )

        if not info.initialized:
            return info

        if "guides" in self.db.list_tables().tables:
            info.guides_count = self.db.open_table("guides").count_rows()

        if "chunks" in self.db.list_tables().tables:
            info.chunks_count = self.db.open_table("chunks").count_rows()

        if "_metadata" in self.db.list_tables().tables:
            table = self.db.open_table("_metadata")
            metadata_list = table.search().limit(1).to_pydantic(DatabaseMetadata)
            if metadata_list:
                metadata = metadata_list[0]
                info.model_name = metadata.model_name
                info.last_indexed_at = metadata.last_indexed_at

        return info
