"""Search quality tests using golden set methodology.

Tests the search_best_practices MCP tool against a set of
expected query-result pairs to ensure search relevance.
"""

import pytest

from mcp_canon.server.mcp import search_best_practices

# Golden set: queries with expected top results
# Format: (query, expected_heading_contains, expected_rank)
GOLDEN_SET = [
    # Rate limiting should match the Rate Limiting section
    {
        "query": "rate limiting envoy configuration",
        "namespace": "exness",
        "expected_heading_contains": "Rate Limiting",
        "expected_in_top_k": 1,
    },
    {
        "query": "rate limiting configuration in istio",
        "namespace": "exness",
        "expected_heading_contains": "Rate Limiting",
        "expected_in_top_k": 3,
    },
    # Sidecar resources
    {
        "query": "istio sidecar memory cpu limits",
        "namespace": "exness",
        "expected_heading_contains": "Sidecar Resource",
        "expected_in_top_k": 1,
    },
    {
        "query": "istio resources configuration",
        "namespace": "exness",
        "expected_heading_contains": "Sidecar Resource",
        "expected_in_top_k": 3,
    },
    # Database exclusion
    {
        "query": "exclude database from mesh traffic",
        "namespace": "exness",
        "expected_heading_contains": "Exclude Databases",
        "expected_in_top_k": 1,
    },
    # Istiod configuration
    {
        "query": "istiod performance tuning",
        "namespace": "exness",
        "expected_heading_contains": "Istiod",
        "expected_in_top_k": 3,
    },
    # Gateway HA
    {
        "query": "istio gateway high availability",
        "namespace": "exness",
        "expected_heading_contains": "Gateway",
        "expected_in_top_k": 3,
    },
]

# Negative set: queries that should return NO relevant results
# These are semantically distant from Istio (L2 distance > 1.1)
# Note: Some tech topics (django, k8s) may be borderline due to shared DevOps context
NEGATIVE_SET = [
    {
        "query": "react hooks useState useEffect tutorial",
        "namespace": "exness",
        "reason": "React frontend is completely unrelated to Istio (L2 ~1.25)",
    },
    {
        "query": "python asyncio coroutines await",
        "namespace": "exness",
        "reason": "Python async programming is unrelated (L2 ~1.15)",
    },
    {
        "query": "machine learning neural network tensorflow",
        "namespace": "exness",
        "reason": "ML topic has no overlap with service mesh",
    },
    {
        "query": "css flexbox grid layout responsive",
        "namespace": "exness",
        "reason": "Frontend CSS is completely unrelated",
    },
]


class TestSearchQuality:
    """Golden set tests for search relevance."""

    @pytest.mark.parametrize(
        "test_case",
        GOLDEN_SET,
        ids=[c["query"][:40] for c in GOLDEN_SET],
    )
    def test_search_returns_expected_result_in_top_k(self, test_case: dict):
        """Test that expected result appears in top K results."""
        result = search_best_practices(
            query=test_case["query"],
            namespace=test_case.get("namespace"),
        )

        assert result["total_results"] > 0, f"No results for query: {test_case['query']}"

        # Get top K results
        k = test_case["expected_in_top_k"]
        top_k_headings = [r["heading"] for r in result["results"][:k]]

        # Check if expected heading is in top K
        expected = test_case["expected_heading_contains"]
        found = any(expected.lower() in h.lower() for h in top_k_headings)

        assert found, (
            f"Expected '{expected}' in top {k} results.\n"
            f"Query: {test_case['query']}\n"
            f"Got: {top_k_headings}"
        )

    def test_search_returns_relevance_scores(self):
        """Test that results have relevance scores in descending order."""
        result = search_best_practices(
            query="istio configuration best practices",
            namespace="exness",
        )

        if result["total_results"] < 2:
            pytest.skip("Need at least 2 results to test ordering")

        scores = [r["relevance_score"] for r in result["results"]]

        # Scores should be in descending order
        assert scores == sorted(scores, reverse=True), f"Scores not in descending order: {scores}"

    def test_empty_query_returns_results(self):
        """Test that a generic query returns some results."""
        result = search_best_practices(
            query="kubernetes configuration",
            namespace="exness",
        )

        assert result["total_results"] > 0, "Expected at least one result"


class TestSearchMetrics:
    """Aggregate search quality metrics."""

    def test_mrr_above_threshold(self):
        """Test Mean Reciprocal Rank is above acceptable threshold."""
        mrr_sum = 0.0
        total = 0

        for test_case in GOLDEN_SET:
            result = search_best_practices(
                query=test_case["query"],
                namespace=test_case.get("namespace"),
            )

            if result["total_results"] == 0:
                continue

            expected = test_case["expected_heading_contains"].lower()

            # Find rank of expected result
            for i, r in enumerate(result["results"]):
                if expected in r["heading"].lower():
                    mrr_sum += 1.0 / (i + 1)
                    break

            total += 1

        mrr = mrr_sum / total if total > 0 else 0.0

        # MRR should be at least 0.5 (expected result in top 2 on average)
        assert mrr >= 0.5, f"MRR {mrr:.2f} is below threshold 0.5"
        print(f"\nMean Reciprocal Rank: {mrr:.2f}")

    def test_precision_at_1(self):
        """Test Precision@1 (percentage of queries where top result is correct)."""
        correct = 0
        total = 0

        for test_case in GOLDEN_SET:
            if test_case["expected_in_top_k"] != 1:
                continue  # Skip if we don't expect top-1 match

            result = search_best_practices(
                query=test_case["query"],
                namespace=test_case.get("namespace"),
            )

            if result["total_results"] == 0:
                continue

            expected = test_case["expected_heading_contains"].lower()
            top_heading = result["results"][0]["heading"].lower()

            if expected in top_heading:
                correct += 1
            total += 1

        p_at_1 = correct / total if total > 0 else 0.0

        # P@1 should be at least 0.6 (60% of queries get correct top result)
        assert p_at_1 >= 0.6, f"Precision@1 {p_at_1:.2f} is below threshold 0.6"
        print(f"\nPrecision@1: {p_at_1:.2f} ({correct}/{total})")


class TestNegativeSet:
    """Tests for queries that should return no relevant results.

    Currently these queries return results because there's no score threshold.
    These tests document the expected behavior once score filtering is implemented.
    """

    @pytest.mark.parametrize(
        "test_case",
        NEGATIVE_SET,
        ids=[c["query"][:40] for c in NEGATIVE_SET],
    )
    def test_analyze_irrelevant_query_scores(self, test_case: dict):
        """Analyze scores for queries that should return empty results.

        This test prints score information to understand the score distribution
        for irrelevant queries. Once we implement score thresholding, these
        queries should return 0 results.
        """
        result = search_best_practices(
            query=test_case["query"],
            namespace=test_case.get("namespace"),
        )

        # For now, just print analysis - tests pass without assertions
        print(f"\nQuery: {test_case['query']}")
        print(f"Reason should be empty: {test_case['reason']}")
        print(f"Results returned: {result['total_results']}")

        if result["total_results"] > 0:
            scores = [r["relevance_score"] for r in result["results"]]
            headings = [r["heading"] for r in result["results"]]
            print(f"Scores: {scores}")
            print(f"Headings: {headings[:3]}")

    @pytest.mark.parametrize(
        "test_case",
        NEGATIVE_SET,
        ids=[c["query"][:40] for c in NEGATIVE_SET],
    )
    def test_irrelevant_queries_return_empty(self, test_case: dict):
        """Test that irrelevant queries return no results.

        Queries that are semantically distant from all guides (e.g., 'django'
        when only Istio guides exist) should return empty results.
        """
        result = search_best_practices(
            query=test_case["query"],
            namespace=test_case.get("namespace"),
        )

        assert result["total_results"] == 0, (
            f"Expected 0 results for irrelevant query.\\n"
            f"Query: {test_case['query']}\\n"
            f"Reason: {test_case['reason']}\\n"
            f"Got {result['total_results']} results"
        )
