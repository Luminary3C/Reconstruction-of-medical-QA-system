import re
import math
import logging
from collections import Counter
from sqlalchemy import text
from app.db.pgvector_client import get_session
from app.core.config import settings

logger = logging.getLogger(__name__)


class KeywordEngine:
    """In-memory BM25 inverted index over knowledge_chunks."""

    def __init__(self, k1: float | None = None, b: float | None = None):
        self._k1 = k1 if k1 is not None else settings.bm25_k1
        self._b = b if b is not None else settings.bm25_b
        self._chunks: list[dict] = []        # [{chunk_id, content, title, tokens, token_counts}]
        self._doc_count: int = 0
        self._avgdl: float = 0.0
        self._df: dict[str, int] = {}        # document frequency for each term

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    async def reload(self) -> None:
        """Load all chunks from PG and rebuild BM25 index."""
        self._chunks.clear()
        self._df.clear()

        async for session in get_session():
            stmt = text("""
                SELECT kc.id, kc.content, kd.title
                FROM knowledge_chunks kc
                JOIN knowledge_documents kd ON kc.document_id = kd.id
                ORDER BY kc.id
            """)
            result = await session.execute(stmt)
            rows = result.fetchall()

            total_len = 0
            for row in rows:
                tokens = self._tokenize(row.content)
                token_counts = Counter(tokens)
                self._chunks.append({
                    "chunk_id": row.id,
                    "content": row.content,
                    "title": row.title,
                    "tokens": tokens,
                    "token_counts": token_counts,
                })
                total_len += len(tokens)
                for term in set(tokens):
                    self._df[term] = self._df.get(term, 0) + 1

            self._doc_count = len(self._chunks)
            self._avgdl = total_len / self._doc_count if self._doc_count else 1.0

        logger.info("KeywordEngine reloaded: %d chunks, %.1f avgdl, %d terms",
                     self._doc_count, self._avgdl, len(self._df))

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """Sync BM25 search. Returns [{chunk_id, content, title, bm25_score}, ...]."""
        if not self._chunks:
            return []

        top_k = top_k or settings.keyword_retrieval_top_k
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for doc in self._chunks:
            score = self._bm25_score(query_tokens, doc)
            if score > 0:
                scored.append({
                    "chunk_id": doc["chunk_id"],
                    "content": doc["content"],
                    "title": doc["title"],
                    "bm25_score": score,
                })

        scored.sort(key=lambda d: d["bm25_score"], reverse=True)
        return scored[:top_k]

    def _bm25_score(self, query_tokens: list[str], doc: dict) -> float:
        score = 0.0
        doc_len = len(doc["tokens"])
        for term in set(query_tokens):
            n = self._df.get(term, 0)
            if n == 0:
                continue
            idf = math.log((self._doc_count - n + 0.5) / (n + 0.5) + 1.0)
            tf = doc["token_counts"].get(term, 0)
            numerator = tf * (self._k1 + 1.0)
            denominator = tf + self._k1 * (1.0 - self._b + self._b * doc_len / self._avgdl)
            score += idf * numerator / denominator
        return score

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
