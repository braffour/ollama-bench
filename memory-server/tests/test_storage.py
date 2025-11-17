"""Tests for ChromaDB storage operations."""
import pytest
import os
import shutil
from storage.chroma_manager import ChromaManager


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    yield str(storage_dir)
    # Cleanup
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)


@pytest.fixture
def chroma_manager(temp_storage_dir, monkeypatch):
    """Create ChromaManager with temporary storage."""
    monkeypatch.setenv("CHROMA_PERSIST_DIR", temp_storage_dir)
    # Reimport to get new config
    import importlib
    import sys
    # Remove from cache if exists
    modules_to_reload = ['memory_server.chroma.client', 'memory_server.storage.chroma_manager']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]
    
    from storage.chroma_manager import ChromaManager
    manager = ChromaManager()
    return manager


def test_store_memory(chroma_manager):
    """Test storing a memory entry."""
    # Mock embedding (768 dimensions for nomic-embed-text)
    embedding = [0.1] * 768
    
    memory_id = chroma_manager.store(
        text="Test memory entry",
        embedding=embedding,
        agent="researcher",
        task="Test task",
        tags=["test", "unit"]
    )
    
    assert memory_id is not None
    assert isinstance(memory_id, str)


def test_search_memory(chroma_manager):
    """Test searching memory."""
    # Store test entries
    embedding1 = [0.1] * 768
    embedding2 = [0.2] * 768
    
    chroma_manager.store(
        text="First test entry",
        embedding=embedding1,
        agent="researcher",
        task="Task 1",
        tags=["test"]
    )
    
    chroma_manager.store(
        text="Second test entry",
        embedding=embedding2,
        agent="strategist",
        task="Task 2",
        tags=["test"]
    )
    
    # Search with query embedding similar to first
    query_embedding = [0.11] * 768  # Similar to embedding1
    results = chroma_manager.search(query_embedding, n_results=2)
    
    assert len(results) > 0
    assert any("First test entry" in r["text"] for r in results)


def test_query_by_tags(chroma_manager):
    """Test querying by tags."""
    # Store entries with different tags
    embedding = [0.1] * 768
    
    chroma_manager.store(
        text="Researcher entry",
        embedding=embedding,
        agent="researcher",
        task="Research task",
        tags=["research", "market"]
    )
    
    chroma_manager.store(
        text="Strategist entry",
        embedding=embedding,
        agent="strategist",
        task="Strategy task",
        tags=["strategy", "planning"]
    )
    
    # Query by agent
    results = chroma_manager.query_by_tags(agent="researcher")
    assert len(results) > 0
    assert all(r["metadata"]["agent"] == "researcher" for r in results)
    
    # Query by tags
    results = chroma_manager.query_by_tags(tags=["research"])
    assert len(results) > 0


def test_get_stats(chroma_manager):
    """Test getting collection statistics."""
    stats = chroma_manager.get_stats()
    
    assert "total_entries" in stats
    assert "collection_name" in stats
    assert stats["collection_name"] == "multi_agent_memory"

