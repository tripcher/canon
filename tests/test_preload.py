"""Tests for embedding model preloading in SearchEngine."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_canon.server.search import SearchEngine


class TestPreloadModel:
    """Test background model preloading."""

    def test_preload_sets_preloading_flag(self):
        """preload_model sets _preloading to True."""
        engine = SearchEngine("/fake/path")
        assert engine._preloading is False

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.0] * 768]
            mock_registry.return_value.get.return_value.create.return_value = mock_func

            engine.preload_model()
            assert engine._preloading is True
            engine._model_ready.wait(timeout=5)

    def test_preload_sets_model_ready_event(self):
        """preload_model sets _model_ready event when done."""
        engine = SearchEngine("/fake/path")
        assert not engine._model_ready.is_set()

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.0] * 768]
            mock_registry.return_value.get.return_value.create.return_value = mock_func

            engine.preload_model()
            ready = engine._model_ready.wait(timeout=5)

            assert ready is True
            assert engine._embedding_func is mock_func

    def test_preload_calls_warmup(self):
        """preload_model calls compute_query_embeddings('warmup') to trigger model load."""
        engine = SearchEngine("/fake/path")

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.0] * 768]
            mock_registry.return_value.get.return_value.create.return_value = mock_func

            engine.preload_model()
            engine._model_ready.wait(timeout=5)

            mock_func.compute_query_embeddings.assert_called_with("warmup")

    def test_preload_error_stored_and_event_set(self):
        """If preload fails, error is stored and event is still set."""
        engine = SearchEngine("/fake/path")

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_registry.return_value.get.return_value.create.side_effect = RuntimeError(
                "Model not found"
            )

            engine.preload_model()
            engine._model_ready.wait(timeout=5)

            assert engine._model_ready.is_set()
            assert engine._embedding_func is None
            assert isinstance(engine._preload_error, RuntimeError)
            assert "Model not found" in str(engine._preload_error)

    def test_preload_runs_in_daemon_thread(self):
        """preload_model runs in a daemon thread."""
        engine = SearchEngine("/fake/path")
        started = threading.Event()

        with patch("mcp_canon.server.search.get_registry") as mock_registry:

            def slow_create(**_kwargs):
                started.set()
                mock_func = MagicMock()
                mock_func.compute_query_embeddings.return_value = [[0.0] * 768]
                return mock_func

            mock_registry.return_value.get.return_value.create.side_effect = slow_create

            engine.preload_model()
            # Should return immediately (non-blocking)
            assert engine._preloading is True
            # Wait for thread to actually start
            started.wait(timeout=5)
            engine._model_ready.wait(timeout=5)


class TestEmbedQueryWithPreload:
    """Test _embed_query interaction with preloading."""

    def test_embed_query_waits_for_preload(self):
        """_embed_query blocks until preload completes."""
        engine = SearchEngine("/fake/path")
        load_started = threading.Event()
        proceed = threading.Event()

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.1] * 768]

            def slow_create(**_kwargs):
                load_started.set()
                proceed.wait(timeout=5)  # Hold until we release
                return mock_func

            mock_registry.return_value.get.return_value.create.side_effect = slow_create

            engine.preload_model()
            load_started.wait(timeout=5)

            # Model is loading but not ready yet
            assert not engine._model_ready.is_set()

            # Start _embed_query in another thread (it should block)
            result = [None]
            query_done = threading.Event()

            def run_query():
                result[0] = engine._embed_query("test query")
                query_done.set()

            query_thread = threading.Thread(target=run_query)
            query_thread.start()

            # Give query thread time to start waiting
            time.sleep(0.1)
            assert not query_done.is_set(), "_embed_query should be blocked"

            # Release the model loading
            proceed.set()

            # Now query should complete
            query_done.wait(timeout=5)
            assert result[0] is not None
            assert len(result[0]) == 768

    def test_embed_query_raises_on_preload_error(self):
        """_embed_query raises the preload error if preload failed."""
        engine = SearchEngine("/fake/path")

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_registry.return_value.get.return_value.create.side_effect = RuntimeError(
                "Download failed"
            )

            engine.preload_model()
            engine._model_ready.wait(timeout=5)

            with pytest.raises(RuntimeError, match="Download failed"):
                engine._embed_query("test query")

    def test_embed_query_without_preload_loads_synchronously(self):
        """Without preload, _embed_query loads the model itself."""
        engine = SearchEngine("/fake/path")

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.5] * 768]
            mock_registry.return_value.get.return_value.create.return_value = mock_func

            assert engine._preloading is False
            result = engine._embed_query("test query")

            assert len(result) == 768
            mock_func.compute_query_embeddings.assert_called_with("test query")

    def test_embed_query_uses_cached_func_after_preload(self):
        """After preload, _embed_query reuses the loaded function."""
        engine = SearchEngine("/fake/path")

        with patch("mcp_canon.server.search.get_registry") as mock_registry:
            mock_func = MagicMock()
            mock_func.compute_query_embeddings.return_value = [[0.1] * 768]
            mock_registry.return_value.get.return_value.create.return_value = mock_func

            engine.preload_model()
            engine._model_ready.wait(timeout=5)

            # First call
            engine._embed_query("query 1")
            # Second call
            engine._embed_query("query 2")

            # create() should have been called only once (during preload)
            mock_registry.return_value.get.return_value.create.assert_called_once()


class TestPreloadRealModel:
    """Integration test: verify real fastembed model loads correctly via preload."""

    def test_preload_loads_real_model(self):
        """preload_model downloads/loads the real ONNX model and produces embeddings."""
        engine = SearchEngine("/fake/path")
        engine.preload_model()

        # Wait for real model load (may download on first run)
        ready = engine._model_ready.wait(timeout=120)
        assert ready, "Model loading timed out"
        assert engine._preload_error is None, f"Preload error: {engine._preload_error}"
        assert engine._embedding_func is not None

        # Verify real embeddings
        vectors = engine._embedding_func.compute_query_embeddings("How to test Python code?")
        assert len(vectors) == 1
        assert len(vectors[0]) == 768  # nomic-embed-text-v1.5-Q default dims
        assert all(isinstance(v, float) for v in vectors[0])
