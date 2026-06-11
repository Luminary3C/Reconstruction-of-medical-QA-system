# Tasks: RAG Core System

## Phase 1: 基础设施搭建 (Infrastructure)

- [x] **T1**: Docker Compose 开发环境
  - docker-compose.yml: PostgreSQL pgvector (5432:5432) + Redis (6379:6379) + RabbitMQ (5672/15672)
  - 数据卷持久化配置
  - 容器健康检查

- [x] **T2**: Java SpringBoot 项目初始化
  - Spring Boot 3 + JDK 17 project scaffold (Maven)
  - 分层包结构: config/controller/service/repository/model/dto/filter
  - application-dev.yml: DB/Redis/RabbitMQ 连接配置, 环境变量注入
  - HikariCP 连接池配置
  - Unified response DTO: `ApiResponse<T>` (code/msg/data/traceId)

- [x] **T3**: Python FastAPI 项目初始化
  - FastAPI project scaffold
  - 分层包结构: api/core/schemas/services/db
  - Pydantic schemas: ChatRequest / ChatResponse / ApiResponse
  - requirements.txt: fastapi, uvicorn, openai, langchain, pgvector, redis, pika, sqlalchemy[asyncio]

## Phase 2: Java API Gateway (Java API 网关)

- [x] **T4**: JWT 认证 + Redis 短期上下文
  - JwtAuthFilter: 拦截 `/api/v1/**`, 解析 JWT, 注入 SecurityContext
  - RedisService: 连接 Redis (6379), 实现 user:chat:{uid}:window (LPUSH/LRANGE/LTRIM)
  - AuthFilter 鉴权成功后读取 Redis 滑动窗口, 注入 request attribute
  - 单测: JWT 解析 + Redis 读写

- [x] **T5**: ChatController + SSE 流式透传
  - `POST /api/v1/chat/ask` → 接收 ChatRequest
  - PythonAgentClient: WebClient 流式调用 Python Agent `POST /v1/chat/completions`
  - SseEmitter: 逐 chunk 透传字节流给前端
  - StringBuilder: 内存累加完整回答文本
  - 单测: WebClient 流式调用 mock

- [x] **T6**: AsyncWriteService — 异步双写
  - 流结束后触发: ① Redis LPUSH 追加对话 (+ 滑动窗口 LTRIM 保持 5 轮)
  - ② RabbitMQ publish — 全量对话消息入队
  - 业务线程立即释放, 不等待写完成
  - 单测: 验证 Redis 队列 + MQ 消息

- [x] **T7**: ChatHistory 接口
  - `GET /api/v1/chat/history/{session_id}` — 查询对话历史
  - `DELETE /api/v1/chat/history/{session_id}` — 清空对话
  - 单测: CRUD 验证

## Phase 3: Python Inference Engine (Python 推理引擎)

- [x] **T8**: OpenAI-compatible API Endpoint
  - `POST /v1/chat/completions` — 接收 OpenAI 格式请求
  - `stream=True` 支持 StreamingResponse
  - Request body 包含 `short_term_context` (Java 传入的 Redis 上下文)

- [x] **T9**: 三路并行召回 (RetrievalService)
  - `search_knowledge_base(query)` → 向量数据库 (MVP: pgvector 同一张表)
  - `search_long_term_memory(query, user_id)` → pgvector 向量检索历史对话
  - `asyncio.gather()` 并行执行
  - 每路调用设置 500ms timeout, 超时降级返回空列表
  - 单测: mock 向量检索返回

- [x] **T10**: 上下文融合 (ContextBuilder)
  - JSON Schema 设计: 短期上下文 + RAG 文档 + 长期记忆 → 统一 System Prompt
  - Prompt 模板: `system_template.jinja2`
  - 优先级: 当前查询 > 短期上下文 > RAG 文档 > 长期记忆
  - 单测: 输入输出 Schema 验证

- [x] **T11**: LLM 流式推理 (LLMService)
  - OpenAI-compatible API 调用 (支持任意 provider)
  - StreamingResponse 逐 chunk 返回
  - 配置: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL 环境变量
  - 单测: mock LLM 流式返回

## Phase 4: 异步持久化 (Async Persistence)

- [x] **T12**: RabbitMQ Consumer (Java 侧)
  - 监听 `chat.persistence.queue`
  - 消费消息: embedding 生成 + MyBatis INSERT → pgvector
  - 死信队列处理: 失败 3 次后入 DLQ, 告警
  - 单测: 消费写入验证

- [x] **T13**: pgvector Schema 建表
  - `chat_messages` 表: id, user_id, session_id, question, answer, embedding (vector(1536)), created_at
  - IVFFlat 索引: 为 embedding 列建向量索引
  - 迁移脚本: Flyway / SQL 文件

## Phase 5: 集成与测试 (Integration)

- [x] **T14**: 端到端集成测试
  - 测试场景: 用户提问 → Java 鉴权 → 拉 Redis 上下文 → 转发 Python
  - Python 三路召回 → LLM 流式 → Java SSE 透传 → Redis 写回 → MQ 消费 → PGSQL 持久化
  - 验证: 全链路无阻塞, SSE 字级输出正常

- [x] **T15**: 限流与基础安全
  - Redis 实现用户级限流: `rate:user:{uid}:minute` (滑动窗口 60s, 最大 30 次)
  - 黑名单 IP 过滤
  - 请求 body 大小限制 (10KB)

- [x] **T16**: Docker Compose 一键启动
  - `docker-compose up -d`: 启动所有服务
  - 启动顺序: PG/Redis/RabbitMQ → Java Gateway → Python Agent
  - 健康检查: `/actuator/health` (Java) + `/health` (Python)