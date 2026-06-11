import asyncio
from app.core.config import settings
from app.db.vector_store import VectorStore
from app.db.pgvector_client import get_session


class RetrievalService:

    def __init__(self):
        self.vector_store = VectorStore()

    async def search_knowledge_base(self, query: str, top_k: int = 5) -> list[dict]:
        """知识库 RAG 检索 — 向量库语义搜索."""
        try:
            return await asyncio.wait_for(
                self.vector_store.search(query, top_k),
                timeout=settings.retrieval_timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            return []

    async def search_long_term_memory(self, query: str, user_id: str, top_k: int = 10) -> list[dict]:
        """长期记忆召回 — pgvector 向量检索历史对话."""
        try:
            result = await asyncio.wait_for(
                self._pgvector_search(query, user_id, top_k),
                timeout=settings.retrieval_timeout_ms / 1000,
            )
            return result
        except asyncio.TimeoutError:
            return []

    async def _pgvector_search(self, query: str, user_id: str, top_k: int) -> list[dict]:
        """按 embedding 相似度检索 pgvector 历史对话."""
        async for session in get_session():
            from sqlalchemy import text
            stmt = text("""
                SELECT id, question, answer, created_at,
                       1 - (embedding <=> :embedding::vector) AS similarity
                FROM chat_messages
                WHERE user_id = :user_id
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """)
            result = await session.execute(
                stmt,
                {"embedding": query, "user_id": user_id, "top_k": top_k},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "question": row.question,
                    "answer": row.answer,
                    "similarity": float(row.similarity) if row.similarity else 0.0,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
                for row in rows
            ]
        return []

    async def parallel_retrieval(self, query: str, user_id: str):
        """三路并行召回（短期上下文由 Java 传入，此处仅 RAG + 长期记忆)."""
        rag_docs, long_term_mems = await asyncio.gather(
            self.search_knowledge_base(query),
            self.search_long_term_memory(query, user_id),
        )
        return rag_docs, long_term_mems
