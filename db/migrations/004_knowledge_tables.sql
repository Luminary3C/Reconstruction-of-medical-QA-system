-- 004_knowledge_tables.sql — RAG knowledge base tables (PostgreSQL + pgvector)

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'text',
    source_path VARCHAR(1000),
    chunk_count INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(2048),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON knowledge_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops);
