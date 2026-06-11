"""
User MCP Client — HTTP transport to Java User MCP Server (Resources).
"""
import asyncio
import os
import httpx


class UserMCPClient:

    def __init__(self):
        base = os.getenv("JAVA_MCP_URL", "http://localhost:8080/mcp")
        self._endpoint = base + "/user"
        self._enabled = os.getenv("MCP_ENABLED", "true").lower() == "true"
        self._client = httpx.AsyncClient(timeout=0.5)

    async def connect(self):
        pass

    async def get_profile(self, user_id: str) -> dict:
        if not self._enabled:
            return {}
        try:
            resp = await asyncio.wait_for(
                self._client.get(self._endpoint + f"/resources/user/{user_id}/profile"),
                timeout=0.5,
            )
            return resp.json().get("data", {})
        except (asyncio.TimeoutError, Exception):
            return {}

    async def get_permissions(self, user_id: str) -> dict:
        if not self._enabled:
            return {}
        try:
            resp = await asyncio.wait_for(
                self._client.get(self._endpoint + f"/resources/user/{user_id}/permissions"),
                timeout=0.5,
            )
            return resp.json().get("data", {})
        except (asyncio.TimeoutError, Exception):
            return {}

    async def close(self):
        await self._client.aclose()