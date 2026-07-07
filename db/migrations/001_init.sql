-- 001_init.sql — pgvector schema (PostgreSQL only)
-- Run automatically by the pgvector Docker image on first start

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(100) NOT NULL,
    session_id  VARCHAR(100) NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages(session_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user
    ON chat_messages(user_id);
