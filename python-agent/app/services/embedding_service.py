import hashlib
import math
import struct
import httpx
from openai import AsyncOpenAI
from app.core.config import settings


class EmbeddingService:
    """Embedding generation — mock by default, switchable to real API via EMBEDDING_MODE=api."""

    EMBEDDING_DIM = settings.embedding_dim

    async def embed(self, text: str) -> list[float]:
        if settings.embedding_mode == "api":
            return await self._api_embed(text)
        return self._mock_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if settings.embedding_mode == "api":
            return await self._api_embed_batch(texts)
        return [self._mock_embed(t) for t in texts]

    # ── Mock: deterministic pseudo-vector from text hash ──

    def _mock_embed(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-vector based on text hash.
        Same text → same vector, values in [-1, 1], dimension = EMBEDDING_DIM.
        """
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        floats: list[float] = []
        for i in range(self.EMBEDDING_DIM):
            # Use byte values directly (0-255), map to [-1, 1], avoid NaN/Inf from raw float32 decoding
            offset = (i * 4) % len(digest)
            n = (digest[offset] << 24 | digest[(offset + 1) % 32] << 16 |
                 digest[(offset + 2) % 32] << 8 | digest[(offset + 3) % 32])
            normalized = (n / 0xFFFFFFFF) * 2.0 - 1.0
            floats.append(normalized)
        # Normalize to unit vector for cosine similarity correctness
        norm = math.sqrt(sum(f * f for f in floats)) or 1.0
        return [f / norm for f in floats]

    # ── API: real OpenAI-compatible embedding endpoint ──

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "sk-placeholder",
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def _api_embed(self, text: str) -> list[float]:
        client = self._get_client()
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=text,
        )
        return resp.data[0].embedding

    async def _api_embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        # Batch in chunks of 100
        results: list[list[float]] = []
        for batch_start in range(0, len(texts), 100):
            batch = texts[batch_start:batch_start + 100]
            resp = await client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
            )
            for item in resp.data:
                results.append(item.embedding)
        return results