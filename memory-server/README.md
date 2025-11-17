# Memory Server

Persistent vector memory service for the multi-agent system using ChromaDB and Ollama embeddings.

## Features

- **Persistent Vector Storage**: ChromaDB with duckdb+parquet backend
- **Semantic Search**: Vector similarity search using Ollama embeddings
- **Metadata Tagging**: Automatic tagging based on agent personas
- **REST API**: FastAPI endpoints for memory operations
- **Integration**: Seamless integration with orchestrator

## Quick Start

### 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 2. Configure Environment

Ensure your `.env` file includes:

```bash
MEMORY_SERVER_URL=http://localhost:8000
CHROMA_PERSIST_DIR=./storage/vector_memory
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_URL=http://localhost:11434/api/embeddings
```

### 3. Pull Embedding Model

```bash
ollama pull nomic-embed-text
```

### 4. Start Memory Server

```bash
python memory-server/app.py
```

Or using uvicorn directly:

```bash
uvicorn memory-server.server.api:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check

```bash
GET /memory/health
```

Returns server status and collection statistics.

### Store Memory

```bash
POST /memory/store
Content-Type: application/json

{
  "text": "Memory content to store",
  "agent": "researcher",
  "task": "Task description",
  "tags": ["optional", "tags"],
  "metadata": {"key": "value"}
}
```

### Search Memory

```bash
POST /memory/search
Content-Type: application/json

{
  "query": "search query text",
  "n_results": 5,
  "agent": "researcher",
  "tags": ["tag1", "tag2"]
}
```

### Query by Tags

```bash
POST /memory/query_by_tags
Content-Type: application/json

{
  "agent": "researcher",
  "tags": ["research", "market_analysis"],
  "limit": 10
}
```

## Architecture

- **ChromaDB**: Vector database with persistent storage
- **Ollama Embeddings**: `nomic-embed-text` model for embeddings
- **FastAPI**: REST API framework
- **Pydantic**: Request/response validation

## Integration

The memory server is automatically integrated into the orchestrator:

1. **Before Agent Execution**: Queries memory for relevant context
2. **After Agent Execution**: Stores agent outputs with metadata

The orchestrator will gracefully handle cases where the memory server is unavailable.

## Testing

Run tests with pytest:

```bash
pytest memory-server/tests/
```

## Storage Location

Memory is stored in `./storage/vector_memory/` by default (configurable via `CHROMA_PERSIST_DIR`).

