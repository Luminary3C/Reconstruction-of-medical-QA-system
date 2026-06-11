import json
from sqlalchemy import text
from app.core.config import settings
from app.db.pgvector_client import get_session
from app.services.embedding_service import EmbeddingService


class VectorStore:

    def __init__(self):
        self.embedding = EmbeddingService()

    async def search(self, query: str, top_k: int = 20) -> list[dict]:
        """Semantic vector search — embed query, find closest chunks."""
        query_vec = await self.embedding.embed(query)
        vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

        async for session in get_session():
            stmt = text("""
                SELECT kc.id, kc.content, kc.chunk_index,
                       kd.title AS doc_title,
                       1 - (kc.embedding <=> :vec::vector) AS similarity
                FROM knowledge_chunks kc
                JOIN knowledge_documents kd ON kc.document_id = kd.id
                ORDER BY kc.embedding <=> :vec::vector
                LIMIT :top_k
            """)
            result = await session.execute(stmt, {"vec": vec_str, "top_k": top_k})
            rows = result.fetchall()
            return [
                {
                    "chunk_id": row.id,
                    "content": row.content,
                    "title": row.doc_title,
                    "chunk_index": row.chunk_index,
                    "similarity": float(row.similarity) if row.similarity else 0.0,
                }
                for row in rows
            ]
        return []

    async def list_sources(self) -> list[dict]:
        """List all knowledge base documents."""
        async for session in get_session():
            stmt = text("SELECT id, title, source_type, chunk_count, created_at FROM knowledge_documents ORDER BY created_at DESC")
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [
                {
                    "source_id": row.id,
                    "name": row.title,
                    "source_type": row.source_type,
                    "doc_count": row.chunk_count,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
                for row in rows
            ]
        return []

    async def add_document(self, title: str, content: str, source_type: str = "text") -> int:
        """Split content into chunks, embed each, insert into DB."""
        chunks = self._split_text(content)
        embeddings = await self.embedding.embed_batch(chunks)

        async for session in get_session():
            # Insert document
            doc_stmt = text("""
                INSERT INTO knowledge_documents (title, source_type, chunk_count)
                VALUES (:title, :source_type, :chunk_count)
                RETURNING id
            """)
            doc_result = await session.execute(doc_stmt, {
                "title": title,
                "source_type": source_type,
                "chunk_count": len(chunks),
            })
            doc_id = doc_result.scalar_one()

            # Insert chunks with embeddings
            for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
                vec_str = "[" + ",".join(str(v) for v in emb) + "]"
                chunk_stmt = text("""
                    INSERT INTO knowledge_chunks (document_id, chunk_index, content, embedding)
                    VALUES (:doc_id, :idx, :content, :vec::vector)
                """)
                await session.execute(chunk_stmt, {
                    "doc_id": doc_id,
                    "idx": i,
                    "content": chunk_text,
                    "vec": vec_str,
                })

            await session.commit()
            return doc_id
        return -1

    async def delete_document(self, document_id: int) -> bool:
        """Delete a document and all its chunks (cascade)."""
        async for session in get_session():
            stmt = text("DELETE FROM knowledge_documents WHERE id = :id")
            result = await session.execute(stmt, {"id": document_id})
            await session.commit()
            return result.rowcount > 0
        return False

    def _split_text(self, content: str) -> list[str]:
        """Simple sliding-window text splitter."""
        size = settings.chunk_size
        overlap = settings.chunk_overlap
        chunks: list[str] = []
        start = 0
        while start < len(content):
            end = start + size
            chunks.append(content[start:end])
            start += size - overlap
            if start >= len(content):
                break
            # Avoid infinite loop if overlap >= size
            if size - overlap <= 0:
                break
        return chunks