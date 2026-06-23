import re
import json
import httpx
from openai import AsyncOpenAI
from app.core.config import settings


class RerankerService:
    """Cross-encoder reranker — refines coarse retrieval results.

    Modes:
      - mock: rule-based scoring (similarity + keyword overlap)
      - local: sentence-transformers cross-encoder (bge-reranker-v2-m3)
      - api: LLM-based batch scoring via Flash model
    """

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key or "sk-placeholder",
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
        return self._client

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int = 0,
        content_key: str = "content",
    ) -> list[dict]:
        """Re-rank documents, return top_n sorted by relevance."""
        if not documents:
            return []

        top_n = top_n or settings.reranker_top_n

        if settings.reranker_mode == "local":
            return await self._local_rerank(query, documents, top_n, content_key)
        if settings.reranker_mode == "api":
            return await self._api_rerank(query, documents, top_n, content_key)
        return self._mock_rerank(query, documents, top_n, content_key)

    # ── Mock: similarity + keyword overlap ──

    def _mock_rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
        content_key: str,
    ) -> list[dict]:
        scored = []
        query_terms = self._tokenize(query)

        for doc in documents:
            semantic = doc.get("similarity", 0.0)
            content = doc.get(content_key, "")
            content_terms = self._tokenize(content)

            if query_terms:
                overlap = len(query_terms & content_terms) / len(query_terms)
            else:
                overlap = 0.0

            final_score = 0.7 * semantic + 0.3 * overlap
            scored.append({**doc, "rerank_score": final_score})

        scored.sort(key=lambda d: d["rerank_score"], reverse=True)
        return scored[:top_n]

    # ── Local: sentence-transformers cross-encoder ──

    async def _local_rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
        content_key: str,
    ) -> list[dict]:
        try:
            from sentence_transformers import CrossEncoder
            model = CrossEncoder(settings.reranker_model)
            pairs = [(query, doc.get(content_key, "")) for doc in documents]
            scores = model.predict(pairs)

            for doc, score in zip(documents, scores):
                doc["rerank_score"] = float(score)

            documents.sort(key=lambda d: d["rerank_score"], reverse=True)
            return documents[:top_n]
        except Exception:
            return self._mock_rerank(query, documents, top_n, content_key)

    # ── API: LLM-based batch scoring ──

    _SCORE_PROMPT = """Score each document's relevance to the user query on a scale of 0-10.
- 10 = directly answers the query
- 5 = partially related
- 0 = completely irrelevant
Return ONLY a JSON array of scores like [8.5, 2.0, 9.0]. No explanation."""

    async def _api_rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
        content_key: str,
    ) -> list[dict]:
        if not documents:
            return []

        # Limit to top 15 docs to keep prompt size reasonable
        batch = documents[:15]
        if len(batch) <= 1:
            batch[0]["rerank_score"] = 10.0
            return batch[:top_n]

        # Truncate each doc to 300 chars for scoring
        docs_text = "\n\n".join(
            f"Doc{i}: {doc.get(content_key, '')[:300]}"
            for i, doc in enumerate(batch)
        )
        user_prompt = (
            f"Query: {query}\n\n"
            f"{docs_text}\n\n"
            f"Score:"
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.gatekeeper_model or settings.llm_model,
                messages=[
                    {"role": "system", "content": self._SCORE_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=80,
            )

            raw = response.choices[0].message.content.strip()
            # Extract JSON array from response
            match = re.search(r"\[[\d.,\s]+\]", raw)
            if match:
                scores = json.loads(match.group())
            else:
                return self._mock_rerank(query, documents, top_n, content_key)

            # Assign scores back
            for i, doc in enumerate(batch):
                doc["rerank_score"] = float(scores[i]) if i < len(scores) else 0.0

            batch.sort(key=lambda d: d["rerank_score"], reverse=True)
            return batch[:top_n]
        except Exception:
            return self._mock_rerank(query, documents, top_n, content_key)

    # ── Utils ──

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Simple tokenization: split on non-alphanumeric, lowercase."""
        return set(re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower()))