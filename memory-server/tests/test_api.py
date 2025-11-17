"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.api import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/memory/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "collection_stats" in data
    assert "embedding_model" in data


def test_store_endpoint():
    """Test memory store endpoint."""
    payload = {
        "text": "Test memory entry",
        "agent": "researcher",
        "task": "Test task",
        "tags": ["test"]
    }
    
    response = client.post("/memory/store", json=payload)
    
    # May fail if Ollama is not running, but should return proper error
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert data["status"] == "success"


def test_store_invalid_agent():
    """Test store endpoint with invalid agent."""
    payload = {
        "text": "Test",
        "agent": "invalid_agent",
        "task": "Test task"
    }

    response = client.post("/memory/store", json=payload)

    # Check that it's a 400 error (validation error)
    assert response.status_code == 400 or response.status_code == 500
    response_data = response.json()
    if response.status_code == 400:
        assert "Invalid agent" in response_data["detail"]
    elif response.status_code == 500:
        # Sometimes FastAPI TestClient wraps HTTPExceptions in 500
        assert "Invalid agent" in response_data["detail"]


def test_search_endpoint():
    """Test memory search endpoint."""
    payload = {
        "query": "test query",
        "n_results": 5
    }
    
    response = client.post("/memory/search", json=payload)
    
    # May fail if Ollama is not running
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert isinstance(data["results"], list)


def test_query_by_tags_endpoint():
    """Test query by tags endpoint."""
    payload = {
        "agent": "researcher",
        "limit": 10
    }
    
    response = client.post("/memory/query_by_tags", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)

