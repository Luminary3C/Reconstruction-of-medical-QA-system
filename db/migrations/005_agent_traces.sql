-- 005_agent_traces.sql — Agent pipeline trace storage (PostgreSQL)

CREATE TABLE IF NOT EXISTS agent_traces (
    id             BIGSERIAL PRIMARY KEY,
    request_id     VARCHAR(64) NOT NULL,
    user_id        VARCHAR(128),
    session_id     VARCHAR(128),
    query          TEXT,

    gate           JSONB,
    retrieval      JSONB,
    generation     JSONB,
    verification   JSONB,

    total_latency_ms FLOAT DEFAULT 0,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traces_request ON agent_traces(request_id);
CREATE INDEX IF NOT EXISTS idx_traces_user ON agent_traces(user_id);