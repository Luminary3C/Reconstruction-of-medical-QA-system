"""
Retrieval MCP Client — stdio transport to Retrieval MCP Server.
"""
import asyncio
import os
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


class RetrievalMCPClient:
    """MCP client for the Retrieval Server (stdio, same process)."""

    def __init__(self):
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._ctx = None
        self._session_ctx = None
        self._enabled = os.getenv("MCP_ENABLED", "true").lower() == "true"

    async def connect(self):
        if not self._enabled:
            return
        try:
            server_params = StdioServerParameters(
                command="uv",
                args=["run", "python", "-m", "app.mcp.servers.retrieval_server"],
            )
            self._ctx = stdio_client(server_params)
            self._read, self._write = await self._ctx.__aenter__()
            self._session_ctx = ClientSession(self._read, self._write)
            self._session = await self._session_ctx.__aenter__()
            await self._session.initialize()
        except Exception:
            self._enabled = False

    async def search_knowledge_base(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._enabled or not self._session:
            return []
        try:
            result = await asyncio.wait_for(
                self._session.call_tool("search_knowledge_base", {"query": query, "top_k": top_k}),
                timeout=0.5,
            )
            import json
            return json.loads(result.content[0].text)
        except asyncio.TimeoutError:
            return []

    async def list_knowledge_sources(self) -> list[dict]:
        if not self._enabled or not self._session:
            return []
        try:
            result = await self._session.call_tool("list_knowledge_sources", {})
            import json
            return json.loads(result.content[0].text)
        except Exception:
            return []

    async def close(self):
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)