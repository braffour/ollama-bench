"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MemoryStoreRequest(BaseModel):
    """Request model for storing memory."""
    text: str = Field(..., description="Raw text content to store")
    agent: str = Field(..., description="Agent persona name")
    task: str = Field(..., description="Task description")
    tags: Optional[List[str]] = Field(default=None, description="Additional tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MemoryStoreResponse(BaseModel):
    """Response model for storing memory."""
    id: str = Field(..., description="Memory entry ID")
    status: str = Field(default="success", description="Operation status")
    message: str = Field(default="Memory stored successfully", description="Status message")


class MemorySearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query text")
    n_results: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    agent: Optional[str] = Field(default=None, description="Filter by agent persona")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")


class MemorySearchResult(BaseModel):
    """Individual search result."""
    id: str
    text: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


class MemorySearchResponse(BaseModel):
    """Response model for semantic search."""
    results: List[MemorySearchResult]
    query: str
    n_results: int


class MemoryQueryRequest(BaseModel):
    """Request model for querying by tags."""
    agent: Optional[str] = Field(default=None, description="Filter by agent persona")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")


class MemoryQueryResponse(BaseModel):
    """Response model for querying by tags."""
    results: List[MemorySearchResult]
    count: int


class MemoryClearRequest(BaseModel):
    """Request model for clearing memory."""
    confirm: bool = Field(default=False, description="Whether to skip confirmation prompts")
    clear_data: bool = Field(default=True, description="Clear memory entries")
    clear_file: bool = Field(default=False, description="Clear persistence file")


class MemoryClearResponse(BaseModel):
    """Response model for clearing memory."""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(default="Memory cleared successfully", description="Status message")
    entries_cleared: int = Field(default=0, description="Number of entries cleared")
    file_deleted: bool = Field(default=False, description="Whether persistence file was deleted")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    collection_stats: Dict[str, Any]
    embedding_model: str

