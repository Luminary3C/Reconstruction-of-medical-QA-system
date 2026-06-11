# Design: RAG Core System

## Architecture

```
                        POST /api/v1/chat/ask
┌──────────┐  JWT       ┌─────────────────────────────────────┐
│  Client  │───────────▶│     Java SpringBoot (API Gateway)   │
│          │            │                                     │
│          │  SSE       │  ┌─────────────────────────────┐    │
│          │◀───────────│  │ AuthFilter (JWT验证)        │    │
│          │            │  │ + Redis 短期上下文拉取       │    │
│          │            │  └─────────────┬───────────────┘    │
│          │            │                │                    │
│          │            │  ┌─────────────▼───────────────┐    │
│          │            │  │ ChatController              │    │
│          │            │  │ - 转发请求到 Python Agent   │    │
│          │            │  │ - SSE 透传字节流给前端      │    │
│          │            │  │ - StringBuilder 拼接全量    │    │
│          │            │  └─────────────┬───────────────┘    │
│          │            │                │                    │
│          │            │  ┌─────────────▼───────────────┐    │
│          │            │  │ AsyncWriteService (流结束)  │    │
│          │            │  │ - Redis: LPUSH 追加队列     │    │
│          │            │  │ - RabbitMQ: publish 消息    │    │
│          │            │  └─────────────┬───────────────┘    │
└──────────┘            └────────────────┼────────────────────┘
                                         │ HTTP (流式转发)
                                         ▼
                        ┌─────────────────────────────────────┐
                        │   Python FastAPI (Inference Engine)  │
                        │                                     │
                        │  POST /v1/chat/completions          │
                        │  (OpenAI-compatible API)            │
                        │                                     │
                        │  ┌─────────────────────────────┐    │
                        │  │ AgentService                │    │
                        │  │                             │    │
                        │  │  Step 1: 接收 Java 转发     │    │
                        │  │         (含短期上下文 JSON)   │    │
                        │  │                             │    │
                        │  │  Step 2: 三路并行召回        │    │
                        │  │  ┌───────┐ ┌───────┐       │    │
                        │  │  │Vector │ │pgvector│       │    │
                        │  │  │ Search│ │Search │       │    │
                        │  │  │(RAG)  │ │(长期) │       │    │
                        │  │  └───┬───┘ └───┬───┘       │    │
                        │  │      │ asyncio │           │    │
                        │  │      │ .gather │           │    │
                        │  │      └────┬────┘           │    │
                        │  │           ▼                │    │
                        │  │  Step 3: ContextBuilder    │    │
                        │  │  融合: 短期 + RAG + 长期    │    │
                        │  │           ▼                │    │
                        │  │  Step 4: LLMService        │    │
                        │  │  StreamingResponse         │    │
                        │  └─────────────────────────────┘    │
                        └──────────────────────────────────────┘
```

## Data Flow: Full Lifecycle

```
   User                Java Gateway           Python Agent         Redis       RabbitMQ      PostgreSQL
    │                      │                      │                  │             │              │
    │① POST /chat/ask      │                      │                  │             │              │
    │─────JWT─────────────▶│                      │                  │             │              │
    │                      │② 验证JWT              │                  │             │              │
    │                      │③ GET user:{uid}:chat ├─▶                │             │              │
    │                      │◀─────[msgs]──────────│                  │             │              │
    │                      │                      │                  │             │              │
    │                      │④ HTTP POST (stream)  │                  │             │              │
    │                      │   + short_term_ctx   │                  │             │              │
    │                      │─────────────────────▶│                  │             │              │
    │                      │                      │⑤ parallel search │             │              │
    │                      │                      │──▶pgvector       │             │              │
    │                      │                      │──▶vectorDB       │             │              │
    │                      │                      │◀──[docs,mems]────│             │              │
    │                      │                      │                  │             │              │
    │                      │                      │⑥ fuse + LLM      │             │              │
    │                      │                      │                  │             │              │
    │                      │⑦ SSE stream ◀────────│                  │             │              │
    │◀────SSE stream───────│  (逐字透传)           │                  │             │              │
    │   (字逐字出现)        │                      │                  │             │              │
    │                      │                      │                  │             │              │
    │                      │⑧ [流结束]             │                  │             │              │
    │                      │  StringBuilder拼好了  │                  │             │              │
    │                      │                      │                  │             │              │
    │                      │⑨ LPUSH user:chat:hist ├─▶               │             │              │
    │                      │                      │  [Q&A]           │             │              │
    │                      │                      │                  │             │              │
    │                      │⑩ publish(chat_queue) ├─────────────────▶│              │              │
    │                      │                      │                  │              │              │
    │                      │                      │                  │  ⑪ consume  │              │
    │                      │                      │                  │              │ INSERT ▶     │
    │                      │                      │                  │              │  (pgvector)  │
    │                      │                      │                  │              │              │
    ▼                      ▼                      ▼                  ▼             ▼              ▼
  返回                   释放线程                 完成               缓存已更新      消息已消费      已持久化
```

## Technology Stack

| Layer | Tech | Purpose |
|-------|------|---------|
| API Gateway | Java 17 + Spring Boot 3 | JWT, SSE Relay, Rate Limit |
| DB Pool | HikariCP | PostgreSQL connection pooling |
| ORM | MyBatis | pgvector vector operations |
| Inference | Python 3.11 + FastAPI | RAG pipeline, LLM streaming |
| AI Framework | LangChain (loaders/splitters) + 自研 Agent core | Knowledge ingestion, Agent loop |
| Short-term Memory | Redis 7 (Docker, 6379:6379) | Session cache, sliding window |
| Long-term Memory | PostgreSQL pgvector (Docker, 5432:5432) | Vector search on historical conversations |
| Message Queue | RabbitMQ | Async write decoupling |
| Container | Docker + Docker Compose | Local dev environment |

## API Design

### Java Gateway

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat/ask` | Chat endpoint (SSE response) |
| GET | `/api/v1/chat/history/{session_id}` | Get conversation history |
| DELETE | `/api/v1/chat/history/{session_id}` | Clear conversation |

### Python Agent (OpenAI-compatible)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | Chat completions with streaming |

### Unified Response Format

```json
{
  "code": 200,
  "msg": "success",
  "data": { },
  "traceId": "uuid-v4"
}
```

## Project Structure

### Java (SpringBoot)

```
java-gateway/
├── src/main/java/com/rag/gateway/
│   ├── config/
│   │   ├── RedisConfig.java
│   │   ├── DataSourceConfig.java
│   │   ├── RabbitMQConfig.java
│   │   └── SecurityConfig.java
│   ├── controller/
│   │   ├── ChatController.java
│   │   └── ChatHistoryController.java
│   ├── service/
│   │   ├── ChatService.java
│   │   ├── RedisService.java
│   │   ├── PythonAgentClient.java
│   │   └── AsyncWriteService.java
│   ├── repository/
│   │   ├── ChatMessageMapper.java
│   │   └── UserMapper.java
│   ├── model/
│   │   ├── ChatMessage.java
│   │   └── User.java
│   ├── dto/
│   │   ├── ChatRequest.java
│   │   ├── ChatResponse.java
│   │   └── ApiResponse.java
│   ├── filter/
│   │   └── JwtAuthFilter.java
│   └── GatewayApplication.java
├── src/main/resources/
│   ├── application.yml
│   ├── application-dev.yml
│   └── mapper/
│       └── ChatMessageMapper.xml
└── pom.xml
```

### Python (FastAPI)

```
python-agent/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── chat.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── schemas/
│   │   ├── chat.py
│   │   └── common.py
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── retrieval_service.py
│   │   ├── context_builder.py
│   │   └── llm_service.py
│   ├── db/
│   │   ├── vector_store.py
│   │   └── pgvector_client.py
│   └── main.py
├── requirements.txt
└── Dockerfile
```

## Redis Key Naming

```
user:session:{user_id}          → 用户会话状态
user:chat:{user_id}:window      → 滑动窗口对话 (LIST, 最近5轮)
user:chat:{user_id}:full        → 完整对话历史引用
rate:user:{user_id}:minute      → 用户级限流计数器
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Java→Python 跨语言延迟 | 同 Docker network, 走 container name DNS |
| pgvector 向量检索慢 | MVP 阶段数据量小, 加 IVFFlat 索引预留 |
| SSE 中断导致 answer 丢失 | StringBuilder 分段写 Redis, 中断可续 |
| LLM streaming 阻塞 | FastAPI StreamingResponse + asyncio |