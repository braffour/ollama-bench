"""ChromaDB client initialization with persistent storage."""
import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# Configuration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./storage/vector_memory")
COLLECTION_NAME = "multi_agent_memory"

# Ensure directory exists
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)


def get_chroma_client():
    """Initialize and return ChromaDB client with persistent storage."""
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    return client


def get_collection():
    """Get or create the multi_agent_memory collection."""
    client = get_chroma_client()
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Multi-agent system memory with vector embeddings"}
    )
    
    return collection

