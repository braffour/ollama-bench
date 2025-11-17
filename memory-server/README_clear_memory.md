# Memory Clearing Utility

This utility provides both CLI and API interfaces for clearing memory from the vector store used by the multi-agent system.

## Overview

The memory clearing utility allows you to:
- Clear memory entries from the vector store
- Delete the persistence file
- View memory statistics
- Use both command-line and REST API interfaces

## CLI Usage

### Basic Commands

```bash
# Show memory statistics
python clear_memory.py --stats

# Clear vector store entries (with confirmation)
python clear_memory.py --clear-store

# Clear vector store entries (without confirmation)
python clear_memory.py --clear-store --yes

# Clear persistence file (with confirmation)
python clear_memory.py --clear-file

# Clear both entries and file (with confirmation)
python clear_memory.py --clear-all

# Clear everything without confirmation
python clear_memory.py --clear-all --yes
```

### Examples

```bash
# Check current memory usage
cd memory-server
python clear_memory.py --stats

# Clear all memory data
python clear_memory.py --clear-all --yes
```

## API Usage

The memory server provides a REST API endpoint for clearing memory programmatically.

### Endpoint

```
POST /memory/clear
```

### Request Body

```json
{
  "confirm": true,
  "clear_data": true,
  "clear_file": false
}
```

### Parameters

- `confirm` (boolean): Whether to skip confirmation prompts (always true for API calls)
- `clear_data` (boolean): Clear memory entries from the vector store
- `clear_file` (boolean): Delete the persistence file

### Response

```json
{
  "status": "success",
  "message": "Memory cleared successfully",
  "entries_cleared": 85,
  "file_deleted": false
}
```

### API Examples

```bash
# Clear memory entries
curl -X POST "http://localhost:8000/memory/clear" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "clear_data": true, "clear_file": false}'

# Clear persistence file
curl -X POST "http://localhost:8000/memory/clear" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "clear_data": false, "clear_file": true}'

# Clear everything
curl -X POST "http://localhost:8000/memory/clear" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "clear_data": true, "clear_file": true}'
```

## Important Notes

- **Irreversible Operation**: Clearing memory cannot be undone. Make sure to backup important data before clearing.
- **Server Restart Required**: After clearing the persistence file, restart the memory server for changes to take effect.
- **API vs CLI**: The API interface is designed for programmatic use and doesn't require confirmations.
- **File Paths**: The utility uses the configured `CHROMA_PERSIST_DIR` from settings.

## Configuration

The utility respects the following configuration:

- `CHROMA_PERSIST_DIR`: Directory containing the vector store files (configured in `.env`)
- Default location: `./storage/vector_memory/vector_store.json`

Make sure the memory server is properly configured before using the clearing utilities.
