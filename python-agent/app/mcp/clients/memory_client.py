"""
Memory MCP Client — HTTP transport to Java Memory MCP Server.
"""
import asyncio
import httpx
from app.core.config import settings
from app.services.embedding_service import EmbeddingService


class MemoryMCPClient:
    """MCP client for Memory Server (Java, HTTP)."""

    def __init__(self):
        base = settings.java_mcp_url if hasattr(settings, 'java_mcp_url') else "http://localhost:8080/mcp"
        self._endpoint = base + "/memory"
        self._enabled = settings.mcp_enabled
        self._client = httpx.AsyncClient(timeout=2.0)
        self.embedding = EmbeddingService()

    async def connect(self):
        pass  # HTTP transport, no persistent connection needed

    async def search_long_term_memory(self, query: str, user_id: str, top_k: int = 10) -> list[dict]:
        if not self._enabled:
            return []
        try:
            # Generate query embedding for pgvector search
            query_vec = await self.embedding.embed(query)
            vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"
            resp = await asyncio.wait_for(
                self._client.post(self._endpoint + "/tools/search_long_term_memory", json={
                    "query": query, "user_id": user_id, "top_k": top_k,
                    "embedding": vec_str,
                }),
                timeout=1.5,
            )
            return resp.json().get("data", [])
        except (asyncio.TimeoutError, Exception):
            return []

    async def save_conversation(self, user_id: str, question: str, answer: str, metadata: dict = None) -> dict:
        if not self._enabled:
            return {"conversation_id": ""}
        try:
            # Embedding is passed via metadata if available
            emb_str = None
            if metadata and "embedding" in metadata:
                emb = metadata["embedding"]
                emb_str = "[" + ",".join(str(v) for v in emb) + "]"
            resp = await self._client.post(self._endpoint + "/tools/save_conversation", json={
                "user_id": user_id, "question": question, "answer": answer,
                "metadata": metadata or {},
                "embedding": emb_str,
            })
            return resp.json().get("data", {})
        except Exception:
            return {"conversation_id": ""}

    async def close(self):
        await self._client.aclose()