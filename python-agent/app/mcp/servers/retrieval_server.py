"""
Retrieval MCP Server — Python, stdio transport.
Exposes Tools for knowledge base vector search.
"""
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.db.vector_store import VectorStore

server = Server("retrieval-server")
vector_store = VectorStore()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_knowledge_base",
            description="Search the knowledge base using semantic vector search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_knowledge_sources",
            description="List available knowledge base sources",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_knowledge_base":
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        results = await vector_store.search(query, top_k)
        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

    if name == "list_knowledge_sources":
        sources = await vector_store.list_sources()
        return [TextContent(type="text", text=json.dumps(sources, ensure_ascii=False))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
