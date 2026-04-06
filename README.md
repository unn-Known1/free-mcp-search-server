# Free MCP Web Search Server

A **zero-API-key** web search server built with MCP (Model Context Protocol) and Flask. No registration, no API keys, completely free.

## Features

- **MCP Protocol Support** - Works with Claude Desktop and other MCP-compatible clients
- **REST API** - HTTP endpoints for easy integration
- **Free Search** - Uses DuckDuckGo (no API key required)
- **Content Extraction** - Extract text, links, and images from any webpage
- **Batch Search** - Search multiple queries at once
- **Built-in Caching** - 5-minute cache for faster responses
- **CORS Enabled** - Works with any frontend

## Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Build the image
docker build -t free-mcp-search .

# Run the container
docker run -p 8080:8080 free-mcp-search
```

### Option 2: Run with Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python mcp_server.py
```

The server starts on **http://localhost:8080**

## REST API Usage

### Web Search
```bash
curl "http://localhost:8080/api/search?query=python%20tutorial&num_results=5"
```

### Extract Page Content
```bash
curl "http://localhost:8080/api/extract?url=https://example.com"
```

### Batch Search
```bash
curl -X POST http://localhost:8080/api/batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["AI news", "Python tips", "Tech trends"], "num_results": 5}'
```

### News Search
```bash
curl "http://localhost:8080/api/news?query=technology"
```

### Health Check
```bash
curl http://localhost:8080/api/health
```

## MCP Server Setup

### For Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "free-web-search": {
      "command": "python",
      "args": ["/path/to/mcp_server.py", "--mcp"],
      "env": {}
    }
  }
}
```

Or using Docker:

```json
{
  "mcpServers": {
    "free-web-search": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "free-mcp-search", "python", "mcp_server.py", "--mcp"]
    }
  }
}
```

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `web_search` | Search the web, returns title, URL, snippet, domain |
| `get_page_content` | Extract content from a webpage |
| `batch_search` | Perform multiple searches at once |
| `search_news` | Search for recent news articles |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_PORT` | 8080 | Server port |
| `MAX_RESULTS` | 20 | Maximum search results |
| `CACHE_TTL` | 300 | Cache TTL in seconds |

## API Response Examples

### Search Response
```json
{
  "query": "python tutorial",
  "count": 5,
  "results": [
    {
      "title": "Python Tutorial - W3Schools",
      "url": "https://www.w3schools.com/python/",
      "snippet": "Python is a widely used general-purpose programming language...",
      "domain": "www.w3schools.com"
    }
  ]
}
```

### Extraction Response
```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "content": "Example Domain This domain is for use in illustrative examples...",
  "links": ["https://www.iana.org/domains/example"],
  "images": []
}
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Client                           │
└─────────────────────┬───────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌───────────────┐           ┌───────────────┐
│  MCP Client  │           │  REST Client  │
└───────┬───────┘           └───────┬───────┘
        │                           │
        ▼                           ▼
┌─────────────────────────────────────────────────────┐
│              FreeMCP Search Server                   │
│  ┌─────────────┐  ┌─────────────────────────────────┐│
│  │ MCP Server │  │         Flask REST API          ││
│  │   (mcp)    │  │  /api/search, /api/extract, etc ││
│  └─────────────┘  └─────────────────────────────────┘│
│                      │                              │
│                      ▼                              │
│  ┌─────────────────────────────────────────────────┐│
│  │           Search Backend (DuckDuckGo)           ││
│  │  • Instant Answer API                            ││
│  │  • HTML Search Fallback                          ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## Deployment

### Deploy to Railway

1. Create a new Railway project
2. Connect your GitHub repo
3. Railway auto-detects Dockerfile
4. Deploy!

### Deploy to Render

1. Create a new Web Service
2. Connect your GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn mcp_server:app`
5. Deploy!

### Deploy to Fly.io

```bash
fly launch
fly deploy
```

## Rate Limits

- 100 requests per minute per IP (REST API)
- MCP has no strict rate limit
- Built-in caching reduces redundant requests

## License

MIT License - Use freely for any purpose.

## Contributing

Contributions welcome! Please open an issue or PR.
