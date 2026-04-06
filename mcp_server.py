#!/usr/bin/env python3
"""
Free MCP Web Search Server
A zero-API-key MCP server for web search using DuckDuckGo
"""

import json
import asyncio
import time
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# MCP SDK imports
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

app = Flask(__name__)
CORS(app)

# Configuration
MAX_RESULTS = 20
CACHE_TTL = 300

# Simple in-memory cache
search_cache: Dict[str, tuple[float, List[Dict]]] = {}


@dataclass
class SearchResult:
    """Web search result model"""
    title: str
    url: str
    snippet: str
    domain: str
    date: Optional[str] = None


@dataclass
class ExtractionResult:
    """Page extraction result model"""
    url: str
    title: str
    content: str
    links: List[str]
    images: List[str]


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return ""


async def duckduckgo_instant_answer(query: str) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo Instant Answer API"""
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            params = {
                "q": query,
                "format": "json",
                "no_redirect": 1,
                "skip_disambig": 1
            }
            response = await client.get(
                "https://api.duckduckgo.com/",
                params=params
            )
            data = response.json()

            # Extract related topics
            for topic in data.get("RelatedTopics", [])[:MAX_RESULTS]:
                if "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else topic.get("Text", "")[:100],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                        "domain": extract_domain(topic.get("FirstURL", ""))
                    })

            # Add definition if available
            if data.get("Definition"):
                results.insert(0, {
                    "title": data.get("Heading", query),
                    "url": data.get("DefinitionURL", ""),
                    "snippet": data.get("Definition", ""),
                    "domain": extract_domain(data.get("DefinitionURL", ""))
                })

        except Exception as e:
            print(f"DDG Instant Answer error: {e}")

    return results


async def duckduckgo_html_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo HTML interface"""
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            params = {
                "q": query,
                "kl": "wt-wt"  # Language/region
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params=params,
                headers=headers
            )

            soup = BeautifulSoup(response.text, "lxml")

            for result in soup.select(".result")[:num_results]:
                title_elem = result.select_one(".result__title a")
                snippet_elem = result.select_one(".result__snippet")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "domain": extract_domain(url)
                    })

        except Exception as e:
            print(f"DDG HTML Search error: {e}")

    return results


async def perform_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """Combined search using multiple backends"""
    # Check cache
    cache_key = f"{query}:{num_results}"
    if cache_key in search_cache:
        cached_time, cached_results = search_cache[cache_key]
        if time.time() - cached_time < CACHE_TTL:
            return cached_results

    # Try DuckDuckGo Instant Answer first
    results = await duckduckgo_instant_answer(query)

    # If not enough results, try HTML search
    if len(results) < num_results:
        html_results = await duckduckgo_html_search(query, num_results)
        # Merge, avoiding duplicates
        existing_urls = {r["url"] for r in results}
        for r in html_results:
            if r["url"] not in existing_urls:
                results.append(r)
                existing_urls.add(r["url"])

    # Update cache
    search_cache[cache_key] = (time.time(), results[:num_results])

    return results[:num_results]


async def extract_page_content(url: str) -> Dict[str, Any]:
    """Extract content from a webpage"""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            content_type = response.headers.get("content-type", "")

            # Only parse HTML
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return {
                    "url": url,
                    "title": "",
                    "content": response.text[:5000],
                    "links": [],
                    "images": []
                }

            soup = BeautifulSoup(response.text, "lxml")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get title
            title = soup.title.string if soup.title else ""

            # Get main content
            main = soup.find("main") or soup.find("article") or soup.find("body")
            content = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            content = "\n".join(line.strip() for line in content.split("\n") if line.strip())

            # Extract links
            links = list(set(a.get("href", "") for a in soup.find_all("a", href=True)
                           if a.get("href", "").startswith("http")))

            # Extract images
            images = list(set(img.get("src", "") or img.get("data-src", "")
                            for img in soup.find_all("img")
                            if img.get("src") or img.get("data-src")))

            return {
                "url": url,
                "title": title.strip() if title else "",
                "content": content[:10000],  # Limit content size
                "links": links[:50],
                "images": images[:20]
            }

        except Exception as e:
            return {
                "url": url,
                "title": "",
                "content": f"Error extracting content: {str(e)}",
                "links": [],
                "images": []
            }


# ==================== MCP Server Setup ====================

server = Server("free-mcp-search")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="web_search",
            description="Search the web for information. Returns title, URL, snippet, and domain for each result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 20)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_page_content",
            description="Extract and parse content from a webpage including text, links, and images.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the webpage to extract content from"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="batch_search",
            description="Perform multiple web searches at once. More efficient than individual searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of search queries (max 10)"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Results per query (default: 5)",
                        "default": 5
                    }
                },
                "required": ["queries"]
            }
        ),
        Tool(
            name="search_news",
            description="Search for recent news articles and headlines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "web_search":
            query = arguments.get("query", "")
            num_results = min(arguments.get("num_results", 10), MAX_RESULTS)

            results = await perform_search(query, num_results)

            if not results:
                return [TextContent(
                    type="text",
                    text=f"No search results found for: {query}"
                )]

            output = f"## Search Results for: {query}\n\n"
            for i, r in enumerate(results, 1):
                output += f"{i}. **{r['title']}**\n"
                output += f"   URL: {r['url']}\n"
                output += f"   {r['snippet']}\n\n"

            return [TextContent(type="text", text=output)]

        elif name == "get_page_content":
            url = arguments.get("url", "")

            content = await extract_page_content(url)

            output = f"## Page Content: {content['url']}\n\n"
            output += f"**Title:** {content['title']}\n\n"
            output += f"**Content:**\n{content['content']}\n\n"
            output += f"**Links found:** {len(content['links'])}\n"
            output += f"**Images found:** {len(content['images'])}\n"

            return [TextContent(type="text", text=output)]

        elif name == "batch_search":
            queries = arguments.get("queries", [])[:10]
            num_results = min(arguments.get("num_results", 5), 10)

            output = f"## Batch Search Results ({len(queries)} queries)\n\n"

            for query in queries:
                output += f"### {query}\n"
                results = await perform_search(query, num_results)

                if results:
                    for i, r in enumerate(results[:3], 1):
                        output += f"{i}. {r['title']} - {r['url']}\n"
                else:
                    output += "No results found.\n"
                output += "\n"

            return [TextContent(type="text", text=output)]

        elif name == "search_news":
            query = arguments.get("query", "")
            num_results = min(arguments.get("num_results", 10), MAX_RESULTS)

            # Search with news focus
            news_query = f"{query} news"
            results = await perform_search(news_query, num_results)

            output = f"## News Results for: {query}\n\n"
            for i, r in enumerate(results, 1):
                output += f"{i}. **{r['title']}**\n"
                output += f"   {r['url']}\n\n"

            return [TextContent(type="text", text=output)]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


# ==================== REST API Routes ====================

@app.route("/api/search", methods=["GET", "POST"])
def api_search():
    """REST API: Web search endpoint"""
    if request.method == "POST":
        data = request.get_json() or {}
        query = data.get("query", request.args.get("query", ""))
        num_results = min(int(data.get("num_results", request.args.get("num_results", 10))), MAX_RESULTS)
    else:
        query = request.args.get("query", "")
        num_results = min(int(request.args.get("num_results", 10)), MAX_RESULTS)

    if not query:
        return jsonify({"error": "Query parameter required"}), 400

    # Run async search
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(perform_search(query, num_results))
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    finally:
        loop.close()


@app.route("/api/extract", methods=["GET", "POST"])
def api_extract():
    """REST API: Extract page content"""
    if request.method == "POST":
        data = request.get_json() or {}
        url = data.get("url", request.args.get("url", ""))
    else:
        url = request.args.get("url", "")

    if not url:
        return jsonify({"error": "URL parameter required"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        content = loop.run_until_complete(extract_page_content(url))
        return jsonify(content)
    finally:
        loop.close()


@app.route("/api/batch", methods=["POST"])
def api_batch():
    """REST API: Batch search"""
    data = request.get_json()
    queries = data.get("queries", [])[:10]
    num_results = min(int(data.get("num_results", 5)), 10)

    if not queries:
        return jsonify({"error": "queries array required"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = {}
        for query in queries:
            results[query] = loop.run_until_complete(perform_search(query, num_results))

        return jsonify({
            "queries": queries,
            "results": results
        })
    finally:
        loop.close()


@app.route("/api/news", methods=["GET"])
def api_news():
    """REST API: News search"""
    query = request.args.get("query", "")
    num_results = min(int(request.args.get("num_results", 10)), MAX_RESULTS)

    if not query:
        return jsonify({"error": "Query parameter required"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(perform_search(f"{query} news", num_results))
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    finally:
        loop.close()


@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "FreeMCP Search Server",
        "version": "1.0.0",
        "features": {
            "mcp_server": True,
            "rest_api": True,
            "cache": True
        }
    })


@app.route("/", methods=["GET"])
def index():
    """Root endpoint - API documentation"""
    return jsonify({
        "service": "FreeMCP Search Server",
        "version": "1.0.0",
        "description": "A zero-API-key web search server using MCP protocol",
        "endpoints": {
            "/api/search?query=term&num_results=10": "Web search",
            "/api/extract?url=https://...": "Extract page content",
            "/api/batch": "POST - Batch search",
            "/api/news?query=term": "News search",
            "/api/health": "Health check"
        },
        "mcp_tools": {
            "web_search": "Search the web",
            "get_page_content": "Extract page content",
            "batch_search": "Multiple searches",
            "search_news": "News search"
        }
    })


# ==================== Main Entry Points ====================

async def run_mcp_server():
    """Run the MCP server with stdio transport"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def run_flask_server():
    """Run the Flask REST API server"""
    from werkzeug.serving import make_server
    port = int(os.environ.get("FLASK_PORT", 8080))
    print(f"Starting Flask server on port {port}...")
    server = make_server('0.0.0.0', port, app)
    server.serve_forever()


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        # Run MCP server
        asyncio.run(run_mcp_server())
    else:
        # Run Flask server (default)
        run_flask_server()
