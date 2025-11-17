"""Configuration loading from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Memory Server Configuration
MEMORY_SERVER_URL = os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")

# Resolve ChromaDB persist directory relative to project root
# From memory-server/config/settings.py, go up to project root
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", os.path.join(_project_root, "storage", "vector_memory"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_EMBEDDING_URL = os.getenv("OLLAMA_EMBEDDING_URL", "http://localhost:11434/api/embeddings")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# Server Configuration
SERVER_HOST = os.getenv("MEMORY_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("MEMORY_SERVER_PORT", "8000"))

