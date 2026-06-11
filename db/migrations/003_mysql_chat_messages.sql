-- 003_mysql_chat_messages.sql — MySQL chat_messages table
-- Note: no pgvector embedding column; embedding field is null for now

CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     VARCHAR(100) NOT NULL,
    session_id  VARCHAR(100) NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
