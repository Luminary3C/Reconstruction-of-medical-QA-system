-- 001_init.sql — only enable pgvector extension
-- Table creation is managed by Alembic (python-agent/alembic/)

CREATE EXTENSION IF NOT EXISTS vector;
