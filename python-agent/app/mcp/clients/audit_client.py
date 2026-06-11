"""
Audit MCP Client — HTTP transport to Java Audit MCP Server.
"""
import httpx
from app.core.config import settings


class AuditMCPClient:

    def __init__(self):
        base = settings.java_mcp_url if hasattr(settings, 'java_mcp_url') else "http://localhost:8080/mcp"
        self._endpoint = base + "/audit"
        self._enabled = settings.mcp_enabled
        self._client = httpx.AsyncClient(timeout=2.0)

    async def connect(self):
        pass

    async def audit_log(self, event_type: str, user_id: str, detail: dict) -> dict:
        if not self._enabled:
            return {"ack": False}
        try:
            resp = await self._client.post(self._endpoint + "/tools/audit_log", json={
                "event_type": event_type, "user_id": user_id, "detail": detail,
            })
            return resp.json().get("data", {"ack": True})
        except Exception:
            return {"ack": False}

    async def close(self):
        await self._client.aclose()