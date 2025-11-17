"""Simple vector store management for memory storage."""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from .simple_vector_store import SimpleVectorStore
import os
from config.settings import CHROMA_PERSIST_DIR


class ChromaManager:
    """Manages vector store operations for memory storage."""

    def __init__(self):
        persist_file = os.path.join(CHROMA_PERSIST_DIR, "vector_store.json")
        self.collection = SimpleVectorStore(persist_file=persist_file)
    
    def store(
        self,
        text: str,
        embedding: List[float],
        agent: str,
        task: str,
        tags: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory entry with text, embedding, and metadata.
        
        Args:
            text: Raw text content
            embedding: Vector embedding
            agent: Agent persona name
            task: Task description
            tags: List of tags
            metadata: Additional metadata dict
            
        Returns:
            Memory entry ID
        """
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Prepare metadata
        entry_metadata = {
            "agent": agent,
            "task": task,
            "tags": ",".join(tags),  # ChromaDB stores as comma-separated string
            "timestamp": timestamp,
            **(metadata or {})
        }
        
        # Store in vector store
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[entry_metadata]
        )
        
        return memory_id
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            n_results: Number of results to return
            where: Optional metadata filter (e.g., {"agent": "researcher"})
            
        Returns:
            List of search results with metadata
        """
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if len(results["distances"]) > 0 and i < len(results["distances"][0]) else None
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def query_by_tags(
        self,
        agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query memories by agent and/or tags.
        
        Args:
            agent: Filter by agent persona
            tags: Filter by tags (any match)
            limit: Maximum results to return
            
        Returns:
            List of matching memory entries
        """
        where = {}
        
        if agent:
            where["agent"] = agent
        
        # Get all entries and filter by tags if needed
        all_results = self.collection.get(where=where if where else None, limit=limit)

        formatted_results = []
        if all_results["ids"]:
            for i in range(len(all_results["ids"])):
                entry_tags = all_results["metadatas"][i].get("tags", "").split(",")

                # Filter by tags if specified
                if tags:
                    if not any(tag.strip() in entry_tags for tag in tags):
                        continue

                result = {
                    "id": all_results["ids"][i],
                    "text": all_results["documents"][i],
                    "metadata": all_results["metadatas"][i]
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        count = self.collection.count()
        return {
            "total_entries": count,
            "collection_name": "multi_agent_memory"
        }

