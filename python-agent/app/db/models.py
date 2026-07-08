"""SQLAlchemy ORM models for PostgreSQL (pgvector) tables."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(2048), nullable=True)
    created_at = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id"),
        Index("idx_chat_messages_user", "user_id"),
        Index("idx_chat_messages_embedding", embedding, postgresql_using="hnsw",
              postgresql_with={}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), server_default="text")
    source_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(2048), nullable=True)
    created_at = mapped_column(DateTime, server_default=func.now())

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_embedding", embedding, postgresql_using="hnsw",
              postgresql_with={}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    gate = mapped_column(JSONB, nullable=True)
    retrieval = mapped_column(JSONB, nullable=True)
    generation = mapped_column(JSONB, nullable=True)
    verification = mapped_column(JSONB, nullable=True)
    total_latency_ms: Mapped[float] = mapped_column(Float, server_default="0")
    created_at = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_traces_request", "request_id"),
        Index("idx_traces_user", "user_id"),
    )
