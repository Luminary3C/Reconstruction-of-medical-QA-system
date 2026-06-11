import re
from app.core.config import settings


class RerankerService:
    """Cross-encoder reranker — refines coarse retrieval results.

    Modes:
      - mock: rule-based scoring (similarity + keyword overlap)
      - local: sentence-transformers cross-encoder (bge-reranker-v2-m3)
      - api: external rerank API (Cohere, Jina, etc.)
    """

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

    # ── API: external rerank service ──

    async def _api_rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
        content_key: str,
    ) -> list[dict]:
        # Placeholder — replace with actual API integration (Cohere, Jina, etc.)
        return self._mock_rerank(query, documents, top_n, content_key)

    # ── Utils ──

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Simple tokenization: split on non-alphanumeric, lowercase."""
        return set(re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower()))