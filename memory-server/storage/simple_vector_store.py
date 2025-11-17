"""Simple in-memory vector store using scikit-learn for testing."""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
from datetime import datetime


class SimpleVectorStore:
    """Simple in-memory vector store with cosine similarity search."""

    def __init__(self, persist_file: str = None):
        """
        Initialize the vector store.

        Args:
            persist_file: Optional file path to persist/load data
        """
        self.vectors: List[List[float]] = []
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.persist_file = persist_file

        if persist_file and os.path.exists(persist_file):
            self._load_from_file()

    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Add vectors, documents, and metadata to the store."""
        for i, (id_val, embedding, document, metadata) in enumerate(zip(ids, embeddings, documents, metadatas)):
            if id_val in self.ids:
                # Update existing
                idx = self.ids.index(id_val)
                self.vectors[idx] = embedding
                self.documents[idx] = document
                self.metadatas[idx] = metadata
            else:
                # Add new
                self.ids.append(id_val)
                self.vectors.append(embedding)
                self.documents.append(document)
                self.metadatas.append(metadata)

        if self.persist_file:
            self._save_to_file()

    def query(
        self,
        query_embeddings: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List]:
        """
        Query the vector store.

        Args:
            query_embeddings: Query embedding vector (single vector)
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dict with ids, documents, metadatas, and distances
        """
        if not self.vectors:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        query_vector = np.array(query_embeddings)
        stored_vectors = np.array(self.vectors)

        # Calculate cosine similarities
        similarities = cosine_similarity([query_vector], stored_vectors)[0]

        # Apply metadata filter if provided
        if where:
            filtered_indices = []
            for i, metadata in enumerate(self.metadatas):
                if all(metadata.get(k) == v for k, v in where.items()):
                    filtered_indices.append(i)
        else:
            filtered_indices = list(range(len(self.vectors)))

        if not filtered_indices:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        # Sort by similarity and get top results
        filtered_similarities = similarities[filtered_indices]
        sorted_indices = np.argsort(filtered_similarities)[::-1]  # Sort descending

        top_indices = sorted_indices[:n_results]
        result_indices = [filtered_indices[i] for i in top_indices]

        # Convert similarities to distances (1 - similarity)
        distances = [1.0 - similarities[i] for i in result_indices]

        return {
            "ids": [[self.ids[i] for i in result_indices]],
            "documents": [[self.documents[i] for i in result_indices]],
            "metadatas": [[self.metadatas[i] for i in result_indices]],
            "distances": [distances]
        }

    def get(
        self,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, List]:
        """Get entries by metadata filter."""
        if not where:
            # Return all entries up to limit
            end_idx = min(limit, len(self.ids))
            return {
                "ids": self.ids[:end_idx],
                "documents": self.documents[:end_idx],
                "metadatas": self.metadatas[:end_idx]
            }

        # Filter by metadata
        filtered_ids = []
        filtered_documents = []
        filtered_metadatas = []

        for i, metadata in enumerate(self.metadatas):
            if all(metadata.get(k) == v for k, v in where.items()):
                filtered_ids.append(self.ids[i])
                filtered_documents.append(self.documents[i])
                filtered_metadatas.append(self.metadatas[i])

                if len(filtered_ids) >= limit:
                    break

        return {
            "ids": filtered_ids,
            "documents": filtered_documents,
            "metadatas": filtered_metadatas
        }

    def count(self) -> int:
        """Return the number of entries in the store."""
        return len(self.ids)

    def _save_to_file(self):
        """Save data to file."""
        if not self.persist_file:
            return

        data = {
            "vectors": self.vectors,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "ids": self.ids,
            "saved_at": datetime.now().isoformat()
        }

        os.makedirs(os.path.dirname(self.persist_file), exist_ok=True)
        with open(self.persist_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_file(self):
        """Load data from file."""
        if not self.persist_file or not os.path.exists(self.persist_file):
            return

        try:
            with open(self.persist_file, 'r') as f:
                data = json.load(f)

            self.vectors = data.get("vectors", [])
            self.documents = data.get("documents", [])
            self.metadatas = data.get("metadatas", [])
            self.ids = data.get("ids", [])
        except Exception as e:
            print(f"Error loading vector store from file: {e}")

