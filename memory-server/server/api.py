"""FastAPI REST API endpoints for memory server."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from server.models import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryClearRequest,
    MemoryClearResponse,
    HealthResponse,
    MemorySearchResult
)
from storage.chroma_manager import ChromaManager
from embeddings.ollama_embedder import OllamaEmbedder
from config.metadata import build_tags, validate_agent, VALID_AGENTS
from config.settings import EMBEDDING_MODEL
from clear_memory import clear_vector_store, clear_simple_vector_store

app = FastAPI(
    title="Memory Server",
    description="Persistent vector memory for multi-agent system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
chroma_manager = ChromaManager()
embedder = OllamaEmbedder()


@app.get("/memory/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        stats = chroma_manager.get_stats()
        return HealthResponse(
            status="healthy",
            collection_stats=stats,
            embedding_model=EMBEDDING_MODEL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/memory/store", response_model=MemoryStoreResponse)
async def store_memory(request: MemoryStoreRequest):
    """
    Store memory with metadata and auto-embedding.
    
    The text is automatically embedded using Ollama, and stored in ChromaDB
    with the provided metadata and tags.
    """
    try:
        # Validate agent
        if not validate_agent(request.agent):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {request.agent}. Valid agents: {VALID_AGENTS}"
            )
        
        # Generate embedding
        embedding = await embedder.embed(request.text)
        
        # Build tags
        tags = build_tags(
            agent=request.agent,
            topic=request.metadata.get("topic") if request.metadata else None,
            output_type=request.metadata.get("output_type") if request.metadata else None,
            utility=request.metadata.get("utility") if request.metadata else None
        )
        
        # Add any additional tags from request
        if request.tags:
            tags.extend(request.tags)
        
        # Store in ChromaDB
        memory_id = chroma_manager.store(
            text=request.text,
            embedding=embedding,
            agent=request.agent,
            task=request.task,
            tags=tags,
            metadata=request.metadata
        )
        
        return MemoryStoreResponse(
            id=memory_id,
            status="success",
            message="Memory stored successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@app.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """
    Semantic search using vector similarity.
    
    The query text is embedded and used to find similar memories.
    """
    try:
        # Generate embedding for query
        query_embedding = await embedder.embed(request.query)
        
        # Build where clause for filtering
        where = None
        if request.agent:
            where = {"agent": request.agent}
        
        # Perform search
        results = chroma_manager.search(
            query_embedding=query_embedding,
            n_results=request.n_results,
            where=where
        )
        
        # Filter by tags if specified
        if request.tags:
            filtered_results = []
            for result in results:
                entry_tags = result["metadata"].get("tags", "").split(",")
                if any(tag.strip() in entry_tags for tag in request.tags):
                    filtered_results.append(result)
            results = filtered_results
        
        # Format results
        formatted_results = [
            MemorySearchResult(
                id=r["id"],
                text=r["text"],
                metadata=r["metadata"],
                distance=r.get("distance")
            )
            for r in results
        ]
        
        return MemorySearchResponse(
            results=formatted_results,
            query=request.query,
            n_results=len(formatted_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/memory/query_by_tags", response_model=MemoryQueryResponse)
async def query_by_tags(request: MemoryQueryRequest):
    """
    Query memories by agent and/or tags.
    
    Returns memories matching the specified filters.
    """
    try:
        # Query by tags
        results = chroma_manager.query_by_tags(
            agent=request.agent,
            tags=request.tags,
            limit=request.limit
        )
        
        # Format results
        formatted_results = [
            MemorySearchResult(
                id=r["id"],
                text=r["text"],
                metadata=r["metadata"]
            )
            for r in results
        ]
        
        return MemoryQueryResponse(
            results=formatted_results,
            count=len(formatted_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/memory/clear", response_model=MemoryClearResponse)
async def clear_memory(request: MemoryClearRequest):
    """
    Clear memory entries and/or persistence file.

    This endpoint allows clearing memory data stored in the vector store.
    Use with caution as this operation cannot be undone.
    """
    try:
        entries_cleared = 0
        file_deleted = False

        # Get initial count for reporting
        initial_count = chroma_manager.get_stats()["total_entries"]

        # Clear memory entries if requested
        if request.clear_data:
            if clear_vector_store(confirm=False):  # API calls don't need confirmation
                entries_cleared = initial_count
            else:
                raise HTTPException(status_code=500, detail="Failed to clear memory entries")

        # Clear persistence file if requested
        if request.clear_file:
            if clear_simple_vector_store(confirm=False):
                file_deleted = True
            else:
                raise HTTPException(status_code=500, detail="Failed to clear persistence file")

        return MemoryClearResponse(
            status="success",
            message="Memory cleared successfully",
            entries_cleared=entries_cleared,
            file_deleted=file_deleted
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear operation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from config.settings import SERVER_HOST, SERVER_PORT
    
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)

