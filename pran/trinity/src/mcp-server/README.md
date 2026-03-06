# Trinity MCP Server

MCP (Model Context Protocol) server for orchestrating Trinity agents. This allows a Head agent (like Cornelius) to manage and communicate with sub-agents via MCP tools.

## Features

- **Agent Management**: List, create, delete, start, stop agents
- **Chat**: Send messages to agents and get responses
- **History & Logs**: Retrieve conversation history and container logs
- **Templates**: List and use pre-configured agent templates

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start in development mode (requires Trinity backend running)
npm run dev

# Or build and run
npm run build
npm start
```

### Docker

```bash
# Start with docker-compose (from project root)
docker-compose up -d mcp-server

# View logs
docker-compose logs -f mcp-server
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | 8080 | Port for MCP server |
| `MCP_TRANSPORT` | httpStream | Transport type: `httpStream` or `stdio` |
| `MCP_REQUIRE_API_KEY` | false | Enable API key authentication |
| `TRINITY_API_URL` | http://localhost:8000 | Trinity backend URL |

**Note**: When `MCP_REQUIRE_API_KEY=true` (recommended for production), no admin credentials are needed. All backend API calls use the user's MCP API key directly from each request.

## API Key Authentication

For production use, enable API key authentication to track who is using the MCP server:

```bash
# Enable API key authentication
MCP_REQUIRE_API_KEY=true npm run dev
```

### Getting an API Key

1. Go to the Trinity web UI: http://localhost:3000/api-keys
2. Click "Create API Key"
3. Name your key (e.g., "My Claude Code Key")
4. Copy the API key - **it's only shown once!**

### Using the API Key

Add to `.mcp.json` with the `headers` option:

```json
{
  "mcpServers": {
    "trinity": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer trinity_mcp_YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### API Key Management

- **Create**: `POST /api/mcp/keys` - Create a new key
- **List**: `GET /api/mcp/keys` - List your keys with usage stats
- **Revoke**: `POST /api/mcp/keys/{id}/revoke` - Disable a key
- **Delete**: `DELETE /api/mcp/keys/{id}` - Permanently delete a key

All key usage is tracked with timestamps and request counts.

## Available Tools

### Agent Management

| Tool | Description |
|------|-------------|
| `list_agents` | List all agents with status |
| `get_agent` | Get specific agent details |
| `create_agent` | Create a new agent |
| `delete_agent` | Remove an agent |
| `start_agent` | Start a stopped agent |
| `stop_agent` | Stop a running agent |
| `list_templates` | List available templates |

### Communication

| Tool | Description |
|------|-------------|
| `chat_with_agent` | Send message to agent |
| `get_chat_history` | Get conversation history |
| `get_agent_logs` | Get container logs |

## Testing

### MCP Inspector

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8080/mcp
```

### Claude Code Integration

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "trinity": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Head Agent (Claude)           │
│  Uses MCP tools to orchestrate agents   │
└────────────────────┬────────────────────┘
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────┐
│         Trinity MCP Server              │
│        (FastMCP @ port 8080)            │
└────────────────────┬────────────────────┘
                     │ HTTP API
                     ▼
┌─────────────────────────────────────────┐
│       Trinity Backend API               │
│       (FastAPI @ port 8000)             │
└────────────────────┬────────────────────┘
                     │ Docker API
                     ▼
┌─────────────────────────────────────────┐
│         Agent Containers                │
│   Running Claude Code instances         │
└─────────────────────────────────────────┘
```

## Development

```bash
# Run TypeScript directly
npm run dev

# Build TypeScript
npm run build

# Run built JavaScript
npm start

# Inspect MCP tools
npm run inspect
```
