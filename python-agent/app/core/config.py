from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    # PostgreSQL pgvector
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rag_db"
    db_user: str = "rag_user"
    db_password: str = "123456"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # RabbitMQ
    mq_host: str = "localhost"
    mq_port: int = 5672
    mq_user: str = "rag_user"
    mq_password: str = "guest"

    # Embedding
    embedding_mode: str = "mock"       # "mock" or "api"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 2048

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Agent
    retrieval_timeout_ms: int = 500
    mcp_enabled: bool = True
    java_mcp_url: str = "http://localhost:8080/mcp"

    # GateKeeper
    gatekeeper_enabled: bool = True
    gatekeeper_model: str = ""

    # Reranker
    reranker_mode: str = "mock"          # mock / local / api
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_top_n: int = 5
    retrieval_coarse_top_k: int = 20

    # Keyword retrieval (BM25)
    keyword_retrieval_top_k: int = 20
    bm25_k1: float = 1.2
    bm25_b: float = 0.75

    # Verification
    verification_enabled: bool = True
    verification_model: str = ""

    model_config = {
        "env_prefix": "",
        "env_file": str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        "extra": "ignore",
    }

settings = Settings()
