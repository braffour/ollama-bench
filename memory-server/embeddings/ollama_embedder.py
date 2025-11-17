"""Ollama embedding service for generating vector embeddings."""
import aiohttp
import json
from typing import List, Optional
from config.settings import OLLAMA_EMBEDDING_URL, EMBEDDING_MODEL


class OllamaEmbedder:
    """Service for generating embeddings using Ollama."""
    
    def __init__(self, model: str = None, base_url: str = None):
        """
        Initialize Ollama embedder.
        
        Args:
            model: Embedding model name (defaults to config)
            base_url: Ollama embedding URL (defaults to config)
        """
        self.model = model or EMBEDDING_MODEL
        self.base_url = base_url or OLLAMA_EMBEDDING_URL
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of float values representing the embedding vector
        """
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.base_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama embedding HTTP {response.status}: {error_text[:200]}")
                    
                    data = await response.json()
                    
                    # Ollama embeddings API returns {"embedding": [...]}
                    if "embedding" in data:
                        return data["embedding"]
                    else:
                        raise Exception(f"Unexpected response format: {list(data.keys())}")
            
            except aiohttp.ClientError as e:
                raise Exception(f"Network error connecting to Ollama: {str(e)}")
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

