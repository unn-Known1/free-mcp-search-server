# Free MCP Web Search Server - Specification

## Project Overview

**Project Name:** FreeMCP Search Server
**Type:** MCP Server with REST API
**Core Functionality:** A zero-API-key web search server using MCP protocol with free search backends
**Target Users:** Developers using Claude Desktop, AI agents, and any application needing web search

## Architecture

### Components
1. **MCP Server (Python)** - Core MCP protocol implementation
2. **REST API (Flask)** - HTTP interface for non-MCP clients
3. **Search Backend** - DuckDuckGo Instant Answers (free, no API key)

### MCP Tools Provided

| Tool | Description | Parameters |
|------|-------------|------------|
| `web_search` | Search the web for queries | query, num_results (default 10) |
| `get_page_content` | Extract content from a URL | url |
| `batch_search` | Perform multiple searches at once | queries (list) |
| `search_news` | Search for recent news | query, num_results |

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET/POST | Web search endpoint |
| `/api/extract` | GET/POST | Extract page content |
| `/api/batch` | POST | Batch search |
| `/api/news` | GET | News search |
| `/api/health` | GET | Health check |

## Technical Stack

- **Language:** Python 3.10+
- **MCP SDK:** mcp (official)
- **Web Framework:** Flask
- **HTTP Client:** httpx (async)
- **HTML Parser:** BeautifulSoup4
- **CORS:** flask-cors

## Search Implementation

### Primary: DuckDuckGo Instant Answer API
- Endpoint: `https://api.duckduckgo.com/`
- Parameters: q, format, no_redirect, skip_disambig
- Returns: Topic summaries, definitions, related topics

### Secondary: DuckDuckGo HTML Search
- Endpoint: `https://html.duckduckgo.com/html/`
- Fallback for when Instant Answer lacks results
- Parse HTML for search results

### Tertiary: Brave Search (Free Tier)
- Endpoint: `https://api.search.brave.com/res/v1/web/search`
- Requires free API key (optional)

## Data Models

### SearchResult
```
{
  "title": str,
  "url": str,
  "snippet": str,
  "domain": str,
  "date": Optional[str]
}
```

### ExtractionResult
```
{
  "url": str,
  "title": str,
  "content": str,
  "links": List[str],
  "images": List[str]
}
```

## Deployment

- **Server:** Flask production server (gunicorn)
- **Port:** 8080
- **CORS:** Enabled for all origins
- **Rate Limiting:** 100 requests/minute per IP

## Configuration

Environment variables:
- `FLASK_PORT`: Server port (default 8080)
- `MAX_RESULTS`: Maximum search results (default 20)
- `CACHE_TTL`: Cache TTL in seconds (default 300)
- `RATE_LIMIT`: Rate limit per minute (default 100)

## Acceptance Criteria

1. ✅ MCP server starts without API keys
2. ✅ web_search tool returns valid results
3. ✅ get_page_content extracts article text
4. ✅ REST API endpoints function correctly
5. ✅ CORS headers properly configured
6. ✅ Error handling for failed requests
7. ✅ No external paid API dependencies
