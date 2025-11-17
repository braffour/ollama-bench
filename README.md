# Ollama Multi-Agent Business Analysis System

A sophisticated multi-agent system that coordinates 7 specialized AI agents to perform comprehensive business analysis, product development, and project planning with real-time web search capabilities via MCP (Model Context Protocol).

## Features

### 🤖 Multi-Agent Coordination (7 Agents)
- **Researcher**: Gathers market insights and business intelligence with web search
- **Strategist**: Develops SaaS concepts and business strategies
- **Product Manager**: Defines product requirements, target users, and success metrics
- **Architect**: Designs high-level system architectures with technical research
- **Project Manager**: Creates detailed project plans with timelines and resources
- **Namer**: Generates creative brand names
- **Copywriter**: Creates compelling marketing copy with brand messaging

### 🔍 MCP Web Search Integration
All agents have access to web search capabilities through the SearXNG MCP server:
- Real-time market research
- Current trend analysis
- Competitive intelligence
- External data gathering

### 🧠 Persistent Memory System
- ChromaDB vector database with persistent storage
- Ollama embeddings for semantic search
- REST API for memory operations
- Automatic result storage and retrieval

### 📊 Advanced Progress Tracking
- Real-time agent status monitoring
- Parallel execution with concurrency control
- Detailed result formatting
- Shared memory state management

## Installation

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables:**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env with your specific configuration
   nano .env
   ```

3. **Install Ollama:**
   ```bash
   # macOS
   brew install ollama

   # Start Ollama service
   ollama serve

   # Pull required model (update OLLAMA_MODEL in .env as needed)
   ollama pull llama3.2
   ```

4. **Setup Memory Server (Optional):**
   ```bash
   # Pull embedding model for memory system
   ollama pull nomic-embed-text

   # Start memory server (runs on port 8000)
   python memory-server/app.py &
   ```

5. **Configure MCP (Web Search):**
   The system uses MCP for web search capabilities. Update `SEARXNG_URL` in your `.env` file to point to your SearXNG instance.

## Usage

### Basic Analysis
```bash
python main.py
```

### Command Line Options
```bash
# Run the full agent analysis
python main.py

# List all generated reports and exports
python main.py list

# Open the latest report in default viewer
python main.py open

# Show help and usage information
python main.py help
```

### Memory Server Commands
```bash
# Start memory server (runs on port 8000)
python memory-server/app.py

# Clear memory data (with confirmation)
python memory-server/clear_memory.py --clear-store

# Clear all memory data without confirmation
python memory-server/clear_memory.py --clear-all --yes

# Show memory statistics
python memory-server/clear_memory.py --stats
```

### Output & Reports
After execution, the system automatically generates comprehensive documentation:

#### 📄 Markdown Reports (`reports/agent_report_YYYY-MM-DD.md`)
- **Executive Summary**: Key metrics and analysis overview
- **Task Overview**: All agent assignments and objectives
- **Individual Agent Results**: Detailed outputs from each of the 7 agents
- **Web Research Findings**: Search results and data gathered
- **Shared Memory State**: Complete inter-agent communication log
- **Analysis Summary**: Cross-agent insights and recommendations
- **📚 References Section**: Complete list of web sources with URLs and metadata

#### 💾 JSON Exports (`exports/agent_data_YYYYMMDD_HHMMSS.json`)
- **Complete structured data** for programmatic access
- **Metadata**: Timestamps, agent counts, web search statistics
- **All agent results** with full fidelity
- **Shared memory** state preservation
- **References data**: All consulted URLs with context

#### 📊 Report Features
- **Professional formatting** suitable for business presentations
- **Source attribution** with complete transparency
- **Timestamp tracking** for audit trails
- **Search analytics** showing research activity
- **Cross-references** between agent outputs

## Architecture

### Project Structure
```
ollama-bench/
├── main.py                    # CLI entry point with report generation
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
├── README.md                # This documentation
├── agents/                  # Agent modules
│   ├── __init__.py
│   ├── master_agent.py      # Master agent coordinator
│   ├── engine.py            # Core execution engine with MCP
│   ├── messages.py          # Message passing infrastructure
│   └── utils.py             # Utility functions
├── memory-server/           # Persistent memory system
│   ├── app.py               # FastAPI server entry point
│   ├── clear_memory.py      # Memory clearing utilities
│   ├── chroma/              # ChromaDB client and configuration
│   ├── config/              # Memory server configuration
│   ├── embeddings/          # Ollama embedding service
│   ├── server/              # REST API endpoints
│   ├── storage/             # Vector store management
│   └── tests/               # Memory server tests
├── storage/                 # Persistent data storage
├── reports/                 # Generated markdown reports
└── exports/                 # Generated JSON data exports
```

### Core Components
- **`main.py`**: CLI interface, task orchestration, automatic report generation
- **`agents/master_agent.py`**: Coordinates parallel agent execution
- **`agents/engine.py`**: Ollama integration, MCP web search, concurrency control
- **`agents/messages.py`**: Inter-agent communication infrastructure
- **`agents/utils.py`**: Configuration validation and utilities
- **`memory-server/app.py`**: FastAPI server for persistent memory operations
- **`memory-server/storage/chroma_manager.py`**: ChromaDB vector store management
- **`memory-server/embeddings/ollama_embedder.py`**: Ollama embedding service
- **`memory-server/server/api.py`**: REST API endpoints for memory operations

### MCP Integration
- **MCPClient**: Handles Model Context Protocol communication
- **Web Search**: Agents can request web searches during execution
- **Tool Calling**: Structured tool use for external data access

### Output Formats
- **Markdown**: Beautiful, readable output formatting
- **JSON**: Structured data for programmatic access
- **Progress Tracking**: Real-time execution monitoring
- **References**: Complete web source citations and URLs

### Memory Server API
The memory server provides REST endpoints for persistent memory operations:

#### Health Check
```bash
GET /memory/health
```

#### Store Memory
```bash
POST /memory/store
Content-Type: application/json

{
  "text": "Memory content to store",
  "agent": "researcher",
  "task": "Task description",
  "tags": ["optional", "tags"]
}
```

#### Search Memory
```bash
POST /memory/search
Content-Type: application/json

{
  "query": "search query text",
  "n_results": 5,
  "agent": "researcher"
}
```

#### Clear Memory
```bash
POST /memory/clear
Content-Type: application/json

{
  "confirm": true,
  "clear_data": true,
  "clear_file": false
}
```

## Configuration

### Environment Variables (.env)
```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.2

# System Configuration
MAX_CONCURRENT=3

# Memory Server Configuration
MEMORY_SERVER_URL=http://localhost:8000
CHROMA_PERSIST_DIR=./storage/vector_memory
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_URL=http://localhost:11434/api/embeddings

# SearXNG MCP Configuration
SEARXNG_URL=http://localhost:8888/search
```

### MCP Settings
The system automatically configures MCP using environment variables. The local MCP configuration at `~/.cursor/mcp.json` should match your `.env` settings.

## Agent Capabilities

### Web Search Integration
Agents can perform web searches by including search requests in their JSON output:

```json
{
  "role": "researcher",
  "result": "Analysis based on web data...",
  "search_requests": [
    "latest SME automation trends 2024",
    "competitor analysis SaaS market"
  ]
}
```

### Agent Workflow & Dependencies
The 7 agents work in a coordinated workflow with shared memory and dependencies:

1. **Researcher** → Provides market insights for all other agents
2. **Strategist** → Creates SaaS concepts for Product Manager
3. **Product Manager** → Defines requirements for Architect and Project Manager
4. **Architect** → Provides technical design for Project Manager
5. **Project Manager** → Creates execution plans using all previous outputs
6. **Namer** → Generates brand names for Copywriter
7. **Copywriter** → Creates marketing copy using brand names and product info

### Parallel Execution
- Concurrent agent processing with dependency management
- Configurable concurrency limits (default: 3 simultaneous agents)
- Automatic result aggregation and memory sharing
- Real-time progress tracking with web search integration

## Output Example

```
🤖 Initializing 7 agents...
📋 Agents: researcher, strategist, product_manager, architect, project_manager, namer, copywriter
🔗 Setting up MCP web search capabilities...
⏳ Starting parallel execution...

🔄 Queueing 7 tasks (max concurrent: 3)
🚀 Agent 'researcher' starting task...
🚀 Agent 'strategist' starting task...
🚀 Agent 'product_manager' starting task...
🔍 Agent 'researcher' requested 2 web searches
  📡 Searching: 'latest SME automation trends 2024'
  📡 Searching: 'SME pain points statistics 2024'
✅ Agent 'researcher' completed successfully
✅ Agent 'strategist' completed successfully
✅ Agent 'product_manager' completed successfully
✅ Agent 'architect' completed successfully
✅ Agent 'project_manager' completed successfully
✅ Agent 'namer' completed successfully
✅ Agent 'copywriter' completed successfully
🔄 All 7 tasks completed processing

✅ All agents completed!
📊 Collected 7 results

📄 Generating comprehensive report...
✅ Report saved to: reports/agent_report_2025-11-16.md
💾 Exporting data for programmatic access...
✅ JSON data exported to: exports/agent_data_20251116_192813.json

🎯 REPORT SUMMARY
📊 Total Agents: 7
🔍 Web Searches: 3
🌐 Sources Consulted: 6
🧠 Memory Entries: 7
📄 Report: reports/agent_report_2025-11-16.md
💾 Data Export: exports/agent_data_20251116_192813.json
```

## 🤝 Contributing

This project demonstrates advanced AI agent coordination with MCP integration for web search capabilities. The system showcases:

- **Multi-agent collaboration** with shared memory and dependencies
- **Real-time web research** via SearXNG MCP integration
- **Professional report generation** with complete source attribution
- **Environment-based configuration** for security and flexibility
- **Parallel processing** with concurrency control

## 📜 License

This project is open-source and demonstrates cutting-edge AI agent orchestration techniques.
