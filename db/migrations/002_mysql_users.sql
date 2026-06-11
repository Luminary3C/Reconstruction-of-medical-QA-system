-- 002_mysql_users.sql — MySQL users table for auth
-- BCrypt hash for root123: $2b$12$l44iWeKHwjHQ9FRw.i9YnOFEXvzvs5cttnkdcdRKDEw0F1m/DFqSW

CREATE TABLE IF NOT EXISTS users (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    plan          VARCHAR(50)  DEFAULT 'free',
    preferences   JSON         DEFAULT NULL,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initialize root user (password: root123)
INSERT INTO users (username, password_hash, plan)
VALUES ('root', '$2b$12$l44iWeKHwjHQ9FRw.i9YnOFEXvzvs5cttnkdcdRKDEw0F1m/DFqSW', 'admin')
ON DUPLICATE KEY UPDATE username=username;
