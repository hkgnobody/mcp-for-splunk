# MCP Server for Splunk

A Model Context Protocol (MCP) server that provides seamless integration between Large Language Models (LLMs), AI agents, and Splunk instances (Enterprise/Cloud). This server exposes Splunk's powerful search and data management capabilities through standardized MCP tools.

## Features

- **MCP-compliant server** using FastMCP framework
- **Multiple transport modes**: stdio (local) and SSE (remote server)
- **Comprehensive Splunk integration** with secure authentication
- **Production-ready deployment** with Docker containerization
- **Health monitoring** and automatic service discovery
- **Real-time communication** with MCP clients
- **Extensive tool set** for Splunk data operations

## Available Tools

### Core Tools
- `get_splunk_health` - Check Splunk connection status and version information
- `list_indexes` - List all accessible Splunk indexes with count
- `run_oneshot_search` - Execute quick Splunk searches with immediate results (best for simple queries)
- `run_splunk_search` - Execute complex searches with progress tracking and detailed job information

### Data Discovery Tools
- `list_sourcetypes` - List all available sourcetypes using metadata command
- `list_sources` - List all data sources using metadata command
- `list_apps` - List installed Splunk apps with properties (name, version, author, etc.)
- `list_users` - List Splunk users and their properties (roles, email, default app, etc.)

### KV Store Tools
- `list_kvstore_collections` - List KV Store collections (all apps or specific app)
- `get_kvstore_data` - Retrieve data from KV Store collections with optional MongoDB-style queries
- `create_kvstore_collection` - Create new KV Store collections with field definitions and indexing

### Configuration Tools
- `get_configurations` - Retrieve Splunk configuration settings from .conf files

## Architecture

### Local MCP Server (Current Implementation)
```
┌─────────────────┐    stdio     ┌─────────────────┐    HTTPS/REST    ┌─────────────────┐
│   MCP Client    │◄────────────►│   MCP Server    │◄───────────────►│  Splunk Server  │
│ (Cursor/Claude) │              │   (stdio mode)  │                 │   Port: 8089    │
│                 │              │   server.py     │                 │                 │
└─────────────────┘              └─────────────────┘                 └─────────────────┘
```

### Remote MCP Server (Future Implementation)
```
┌─────────────────┐    HTTP/SSE   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄─────────────►│     Traefik     │◄──►│   MCP Server    │◄──►│  Splunk Server  │
│  (Web Agents)   │               │  Load Balancer  │    │   (SSE mode)    │    │   Port: 8089    │
│                 │               │   Port: 8001    │    │   Port: 8000    │    │                 │
└─────────────────┘               └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+ with uv package manager
- Docker and Docker Compose (for Splunk setup)
- Splunk Enterprise or Cloud instance
- Valid Splunk credentials

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mcp-server-for-splunk
```

### 2. Configure Environment

```bash
cp env.example .env
```

Edit `.env` file with your Splunk details:

```bash
SPLUNK_HOST=localhost
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_SCHEME=http
VERIFY_SSL=false
```

### 3. Install Dependencies with UV

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### 4. Start Local Splunk (for development)

```bash
# Option A: Use the automated script (Recommended)
chmod +x scripts/run_splunk.sh
./scripts/run_splunk.sh

# Option B: Use docker-compose directly
docker-compose -f docker-compose-splunk.yml up -d

# Verify Splunk is running
curl -k https://localhost:8089/services/server/info
```

### 5. Run MCP Server (stdio mode)

```bash
# Activate virtual environment and run server
uv run python src/server.py
```

## Development Setup

### Option 1: Local MCP Server Development

This setup is for contributing to the current stdio-based MCP server implementation:

#### 1. Python Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server-for-splunk

# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

#### 2. Start Splunk for Local Development

You can start Splunk using either the provided script or docker-compose directly:

**Option A: Using the run_splunk.sh script (Recommended)**

```bash
# Make the script executable
chmod +x scripts/run_splunk.sh

# Start Splunk with automated setup
./scripts/run_splunk.sh

# Or rebuild Docker image if needed
./scripts/run_splunk.sh --rebuild
```

The script automatically:
- Checks for required dependencies (Docker, docker-compose)
- Handles ARM64 architecture detection for macOS
- Stops any existing containers
- Starts Splunk with proper configuration
- Waits for Splunk to be fully ready
- Provides connection details and useful commands

**Option B: Using docker-compose directly**

```bash
# Start Splunk using the development docker-compose file
docker-compose -f docker-compose-splunk.yml up -d

# Check Splunk status
docker-compose -f docker-compose-splunk.yml ps

# View Splunk logs
docker-compose -f docker-compose-splunk.yml logs -f so1

# Access Splunk Web UI
open http://localhost:9000
# Login: admin / Chang3d!
```

**Splunk Access Information:**
- **Web UI**: http://localhost:9000
- **Username**: admin
- **Password**: Chang3d!
- **Management Port**: 8089 (for MCP server connection)
- **HEC Port**: 8088 (for data ingestion)

#### 3. Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your Splunk settings (defaults work with docker-compose-splunk.yml)
SPLUNK_HOST=localhost
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_SCHEME=http
VERIFY_SSL=false
```

#### 4. Run and Test MCP Server

```bash
# Run MCP server in stdio mode
uv run python src/server.py

# In another terminal, test with MCP Inspector
npx @modelcontextprotocol/inspector uv run python src/server.py

# Or test with simple client
python test_mcp_client.py
```

#### 5. Add MCP Server to Cursor IDE

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-server-for-splunk/",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_PORT": "8089",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!",
        "SPLUNK_SCHEME": "http",
        "VERIFY_SSL": "false"
      }
    }
  }
}
```

#### 6. Using MCP Inspector

The MCP Inspector provides a web-based interface for testing MCP tools:

```bash
# Install and run MCP Inspector
npx @modelcontextprotocol/inspector uv run python src/server.py

# This will:
# 1. Start your MCP server in stdio mode
# 2. Open browser at http://localhost:5173
# 3. Connect to your server automatically

# Features:
# - Browse all available tools
# - Test tools with custom parameters
# - View real-time responses
# - Debug connection issues
```

### Option 2: Docker-based Development

This setup is for developing the remote server implementation and containerized deployment:

#### 1. Build and Run with Docker

```bash
# Build the Docker image
docker build -t mcp-splunk-server .

# Run with docker-compose (includes Traefik load balancer)
docker-compose up -d

# View logs
docker-compose logs -f mcp-server
```

#### 2. Access Services

- **MCP Server**: http://localhost:8001/mcp/sse
- **MCP Inspector**: http://localhost:6274
- **Traefik Dashboard**: http://localhost:8080
- **Splunk Web**: http://localhost:9000

#### 3. Testing Remote Server

```bash
# Test SSE endpoint
curl http://localhost:8001/mcp/sse

# Use external MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8001/mcp/sse
```

## Available Scripts

### Splunk Development Script

The project includes a comprehensive script for setting up Splunk development environment:

```bash
# Make script executable
chmod +x scripts/run_splunk.sh

# Start Splunk with all dependencies
./scripts/run_splunk.sh

# Rebuild Docker image and start
./scripts/run_splunk.sh --rebuild
```

**Script Features:**
- **Dependency Checking**: Automatically verifies Docker and docker-compose are installed
- **Architecture Detection**: Handles ARM64 (Apple Silicon) compatibility automatically
- **Health Monitoring**: Waits for Splunk to be fully ready before completing
- **Color-coded Output**: Easy-to-read status messages with emojis
- **Error Handling**: Graceful cleanup on failures
- **Useful Information**: Provides connection details and helpful commands

**Script Output:**
- Splunk Web UI access information
- Default credentials (admin/Chang3d!)
- Port information for different services
- Helpful commands for logs and management

## Package Management with UV

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management:

### Key Files

- `pyproject.toml` - Project configuration and dependencies
- `uv.lock` - Locked dependency versions
- `.python-version` - Python version specification

### Common Commands

```bash
# Install all dependencies
uv sync

# Add new dependency
uv add requests

# Add development dependency
uv add --dev pytest

# Run scripts
uv run python src/server.py

# Update dependencies
uv lock --upgrade

# Show dependency tree
uv tree
```

## Integration with Google ADK Agents

This MCP server can be integrated with agents built using Google's Agent Development Kit (ADK). 

### Using MCPToolset in ADK

Based on the [Google ADK MCP documentation](https://google.github.io/adk-docs/tools/mcp-tools/#mcptoolset-class), you can integrate this Splunk MCP server into your ADK agents:

#### Example ADK Agent with Splunk MCP Tools

```python
# agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Define your Agent with MCPToolset for Splunk
splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='splunk_assistant',
    instruction="""You are a Splunk expert assistant. Use the available Splunk tools to:
    - Check system health and connectivity
    - Search and analyze data
    - Manage indexes, sourcetypes, and data sources
    - Work with KV Store collections
    - Retrieve configuration information
    
    Always verify connectivity with get_splunk_health before performing other operations.""",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='uv',
                args=[
                    '--directory', '/path/to/mcp-server-for-splunk/',
                    'run', 'python', 'src/server.py'
                ],
                env={
                    'SPLUNK_HOST': 'localhost',
                    'SPLUNK_PORT': '8089',
                    'SPLUNK_USERNAME': 'admin',
                    'SPLUNK_PASSWORD': 'Chang3d!',
                    'SPLUNK_SCHEME': 'http',
                    'VERIFY_SSL': 'false'
                }
            ),
            # Optional: filter specific tools
            tool_filter=[
                'get_splunk_health',
                'run_oneshot_search',
                'list_indexes',
                'list_sourcetypes'
            ]
        )
    ],
)
```

#### Example __init__.py for ADK Web

```python
# __init__.py
from . import agent
```

#### Running with ADK Web

```bash
# In your ADK agent directory
adk web

# Your Splunk agent will be available in the ADK Web UI
# Test with queries like:
# "Check Splunk health status"
# "List all available indexes"
# "Search for errors in the last hour"
```

### Key ADK Integration Points

1. **MCPToolset Class**: Automatically handles connection management and tool discovery
2. **StdioServerParameters**: Configures stdio transport for local MCP server
3. **Tool Filtering**: Optionally expose only specific tools to your agent
4. **Environment Variables**: Securely pass Splunk credentials to the MCP server

For remote server integration (future), use `SseServerParams` instead:

```python
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

# For remote server (future implementation)
MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8001/mcp/sse",
        headers={"Authorization": "Bearer your-token"}
    )
)
```

## Project Documentation

### Current Implementation Status

- ✅ **stdio MCP Server**: Fully implemented and tested
- ✅ **Splunk Integration**: Complete with 12 tools covering all major Splunk operations
- ✅ **Local Development**: Full setup with docker-compose-splunk.yml
- ✅ **MCP Inspector Support**: Working with both local and remote inspection
- ✅ **Cursor IDE Integration**: Configured and tested
- ⏳ **Remote SSE Server**: Partially implemented, needs production hardening
- ⏳ **Google ADK Integration**: Documented with examples
- ⏳ **Production Deployment**: Docker setup available, needs scaling configuration

### Configuration Files

- **mcp.json**: MCP server configurations for various clients
- **pyproject.toml**: Python project configuration with uv package management
- **docker-compose-splunk.yml**: Standalone Splunk development environment
- **docker-compose.yml**: Full production stack with Traefik
- **.env**: Environment variables for Splunk connection

### Documentation Structure

```
docs/
├── business-case.md           # Business justification and use cases
└── prds/
    ├── main-prd-mcp-server-for-splunk.md  # Main product requirements
    └── mvp-prd.md             # MVP specifications
```

## Monitoring and Troubleshooting

### Health Checks

```bash
# Check MCP server (stdio mode)
echo '{"jsonrpc": "2.0", "id": 1, "method": "ping"}' | uv run python src/server.py

# Check Splunk connection
uv run python -c "from src.splunk_client import get_splunk_service; print(get_splunk_service().info)"

# Check Docker services
docker-compose -f docker-compose-splunk.yml ps
```

### Common Issues

1. **Splunk Connection Failed**
   ```bash
   # Verify Splunk is running
   curl -k https://localhost:8089/services/server/info
   
   # Check credentials in .env file
   # Verify network connectivity
   ```

2. **MCP Server Not Starting**
   ```bash
   # Check Python environment
   uv run python --version
   
   # Verify dependencies
   uv sync
   
   # Check logs
   uv run python src/server.py --verbose
   ```

3. **Tool Execution Errors**
   ```bash
   # Test individual tools with MCP Inspector
   npx @modelcontextprotocol/inspector uv run python src/server.py
   
   # Check Splunk permissions for the user
   # Verify index access and search capabilities
   ```

### Logs

```bash
# MCP Server logs
tail -f src/logs/mcp_splunk_server.log

# Splunk container logs
docker-compose -f docker-compose-splunk.yml logs -f so1

# Docker services logs
docker-compose logs -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the local development setup
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

### Development Workflow

```bash
# Setup development environment
uv sync
source .venv/bin/activate

# Start Splunk for testing (automated script)
chmod +x scripts/run_splunk.sh
./scripts/run_splunk.sh

# Or start Splunk manually
docker-compose -f docker-compose-splunk.yml up -d

# Run tests
uv run pytest

# Format code
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Check the `/docs` directory for detailed guides
- **MCP Inspector**: Use for interactive testing and debugging
- **Community**: Join discussions for help and best practices

## Next Steps

1. **Remote Server Hardening**: Complete SSE server implementation for production
2. **Authentication**: Add token-based authentication for remote access
3. **Caching**: Implement response caching for improved performance
4. **Monitoring**: Add Prometheus metrics and Grafana dashboards
5. **Testing**: Expand test coverage and add integration tests
6. **Documentation**: Create video tutorials and advanced use cases
