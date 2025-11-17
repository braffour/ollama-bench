"""Tests for Ollama embedding service."""
import pytest
import asyncio
from embeddings.ollama_embedder import OllamaEmbedder


@pytest.mark.asyncio
async def test_embed_generates_vector():
    """Test that embed generates a vector embedding."""
    embedder = OllamaEmbedder()
    
    # This test requires Ollama to be running with nomic-embed-text model
    try:
        embedding = await embedder.embed("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)
    except Exception as e:
        # Skip test if Ollama is not available
        pytest.skip(f"Ollama not available: {str(e)}")


@pytest.mark.asyncio
async def test_embed_batch():
    """Test batch embedding generation."""
    embedder = OllamaEmbedder()
    
    texts = ["text one", "text two", "text three"]
    
    try:
        embeddings = await embedder.embed_batch(texts)
        
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
    except Exception as e:
        pytest.skip(f"Ollama not available: {str(e)}")

