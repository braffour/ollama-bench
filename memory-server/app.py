"""Main entry point for Memory Server."""
import uvicorn
from server.api import app
from config.settings import SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info"
    )

