# 医疗问答系统 (Medical QA RAG System)

基于 Agent 范式的医疗问答系统，采用 Java Gateway + Python Agent 双服务架构，实现安全审核、智能检索决策、流式生成与出口校验的分层 Agent 流程。

## 系统架构

```
                         ┌─────────────────────────────────────────────────────────┐
                         │                    用户浏览器                              │
                         │              Vue 3 + Pinia + TypeScript                   │
                         └──────────┬───────────────────────┬─────────────────────┘
                                    │ SSE                   │ SSE
                                    ▼                       ▼
                         ┌──────────────────┐    ┌──────────────────┐
          Python 直连 ──►│  /v1/*           │    │  /api/v1/*       │◄── Java 网关
                         │  Vite Proxy      │    │  Vite Proxy      │
                         │  → localhost:8000 │    │  → localhost:8080 │
                         └────────┬─────────┘    └────────┬─────────┘
                                  │                        │
                                  ▼                        ▼
┌──────────────────────────────────────────┐   ┌──────────────────────────────────────┐
│           Python Agent (FastAPI)          │   │         Java Gateway (Spring Boot)    │
│                                          │   │                                        │
│  ┌────────────┐  ┌────────────────────┐  │   │  ┌──────────┐  ┌───────────────────┐  │
│  │ GateKeeper │  │ Optimistic Retr.   │  │   │  │ JWT Auth  │  │ Rate Limit        │  │
│  │ 意图分类    │  │ 并行检索           │  │   │  │ Filter    │  │ Filter            │  │
│  └─────┬──────┘  └────────┬───────────┘  │   │  └────┬─────┘  └───────────────────┘  │
│        │                  │              │   │       │                               │
│  ┌─────▼──────────────────▼───────────┐ │   │  ┌────▼─────────────────────────────┐  │
│  │     RRF Merge → Reranker → LLM     │ │   │  │ ChatController → PythonAgentClient │  │
│  │     流式生成 + Verification        │ │   │  │ SSE 透传 Python Agent 响应         │  │
│  └─────────────────────────────────────┘ │   │  └──────────────────────────────────┘  │
│                                          │   │                                        │
│  MCP Clients (HTTP)                      │   │  MCP Server (HTTP)                      │
│  ┌──────────┐ ┌───────┐ ┌────────────┐  │   │  ┌──────────┐ ┌─────────┐ ┌────────┐  │
│  │ Memory   │ │ Audit │ │ User       │  │◄──►│  │ Memory   │ │ Audit   │ │ User   │  │
│  │ Client   │ │ Client│ │ Client     │  │   │  │ Handler  │ │ Handler │ │Handler │  │
│  └─────┬────┘ └───┬───┘ └────────────┘  │   │  └────┬─────┘ └────┬────┘ └────────┘  │
│        │          │                      │   │       │             │                   │
└────────┼──────────┼──────────────────────┘   └───────┼─────────────┼───────────────────┘
         │          │                                    │             │
         ▼          ▼                                    ▼             ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                           Infrastructure                                    │
  │  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────────────┐ │
  │  │ PostgreSQL  │  │  Redis   │  │ RabbitMQ │  │         MySQL            │ │
  │  │ + pgvector  │  │  短期记忆 │  │ 异步队列  │  │         用户表           │ │
  │  │ 知识库+审计  │  │  限流    │  │          │  │         聊天记录          │ │
  │  └────────────┘  └──────────┘  └──────────┘  └───────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────────────┘
```

## Agent 问答流程

```
用户问题 ──────────────────────────────────────────────────────────────────────
    │
    ├─── asyncio.create_task ──► GateKeeper.check() (Flash, ~300ms)
    │                            单次 LLM 调用，返回 JSON:
    │                            {intent, rejection_type, reason,
    │                             safety_tags, needs_rag, needs_memory,
    │                             rewritten_query}
    │
    ├─── asyncio.create_task ──► _optimistic_retrieval()
    │                            并行: vector_store.search() + keyword_engine.search()
    │
    ▼ (等 GateKeeper 返回)
    │
    ├── intent=REJECT ────────► 丢弃检索结果 → 模板直出 (<1ms)
    │                            6 种拒答模板: drug_dosage/diagnosis/
    │                            emergency/prescription/treatment_plan/default
    │                            TTFT ≈ 300ms
    │
    ├── intent=CLARIFY ───────► 丢弃检索结果 → 关键词匹配追问模板
    │                            5 种症状模板: 头痛/腹痛/胸痛/皮肤/失眠
    │                            TTFT ≈ 300ms
    │
    └── intent=SIMPLE/HISTORY ► 等检索结果就绪
                                 │
                                 ├── [HISTORY] MemoryMCPClient → Java MCP → PG 长期记忆
                                 │
                                 ├── RRF 合并 (k=60): 语义检索 + BM25 关键词
                                 │
                                 ├── Reranker (Flash LLM batch scoring)
                                 │   → top_n=5
                                 │
                                 ├── ContextBuilder: 按意图选 Jinja2 模板
                                 │   ├── simple_qa.j2    独立知识问答
                                 │   ├── history_chat.j2  多轮对话 + 长期记忆
                                 │   └── clarify.j2      追问后续回答
                                 │
                                 ├── LLM.stream_chat() 流式生成 → 逐 token SSE
                                 │
                                 ├── Verification (async fire-and-forget)
                                 │   └── 事实一致性 + 安全合规 + 置信度
                                 │       → 低置信度推送 verification SSE 事件
                                 │
                                 ├── Sources SSE 事件 (引用文档 + 相关度)
                                 │
                                 └── Post-process (async)
                                     ├── Embedding 持久化 → PG chat_messages
                                     ├── 审计日志 → MCP → PG agent_traces
                                     └── Java Gateway → Redis 短期记忆更新
```

## 核心模块详解

### 1. GateKeeper — 安全审核 + 意图分类 + 查询改写

单次轻量 LLM 调用（Flash 模型），10 个 few-shot 示例驱动，返回结构化 JSON：

| 字段 | 说明 |
|------|------|
| `intent` | `simple` / `history` / `clarify` / `reject` |
| `rejection_type` | `drug_dosage` / `diagnosis` / `emergency` / `prescription` / `treatment_plan` |
| `reason` | 分类理由 |
| `safety_tags` | 安全标签列表 |
| `needs_rag` | 是否需要知识库检索 |
| `needs_memory` | 是否需要长期记忆召回 |
| `rewritten_query` | 指代消解后的改写查询 |

**拒答模板**：6 种预设模板，根据 `rejection_type` 直接生成回复，无需二次 LLM 调用。
**追问模板**：5 种症状关键词匹配模板（头痛/腹痛/胸痛/皮肤/失眠），无匹配则使用通用追问。

### 2. 乐观并行检索 (Optimistic Retrieval)

GateKeeper 与检索**同时发起**，不串行等待：

```
用户输入 ──┬── GateKeeper (~300ms)
           └── 语义检索 + BM25检索 (~200ms)
                    │
              GateKeeper 返回后:
              - reject/clarify → cancel 检索
              - simple/history → 使用已就绪的检索结果
```

三路检索：
- **语义检索**：pgvector 余弦相似度，`<=>` 操作符，top_k=20
- **关键词检索**：内存 BM25 倒排索引，top_k=20，k1=1.2, b=0.75
- **长期记忆**：通过 MCP HTTP 调用 Java Gateway，pgvector 检索用户历史对话

### 3. RRF 合并 + Reranker

**RRF (Reciprocal Rank Fusion)**，k=60：
- 合并语义 + 关键词检索结果，按 chunk_id 去重
- 保留 top_k=20 个唯一文档

**Reranker** 精排 top_n=5，三种模式：
- `mock`：0.7×similarity + 0.3×keyword_overlap
- `local`：sentence-transformers CrossEncoder（BAAI/bge-reranker-v2-m3）
- `api`：LLM-based batch scoring（Flash 模型，每批 15 文档，截取 300 字符评分）

### 4. Context Builder — 医疗专用 Prompt

三个 Jinja2 模板，按意图选择：

| 模板 | 意图 | 输入变量 |
|------|------|----------|
| `simple_qa.j2` | simple | user_query, rag_docs |
| `history_chat.j2` | history | short_term_context, rag_docs, long_term_memories |
| `clarify.j2` | clarify | query |

模板内含医疗安全规则、few-shot 示例、知识库文档引用格式。

### 5. Verification — 出口校验

流式生成结束后异步执行（fire-and-forget），不阻塞响应：

1. **事实一致性**：回答是否与知识库文档矛盾
2. **安全合规**：是否推荐用药/给出诊断/遗漏免责声明
3. **置信度评估**：high / medium / low

校验结果通过 SSE `verification` 事件推送到前端，低置信度时追加免责声明。

### 6. 知识库管理

- **文档上传**：支持 .txt / .pdf / .md / .docx 格式
- **PDF 解析**：pymupdf (fitz) 提取文本
- **文本切片**：LangChain `RecursiveCharacterTextSplitter`，分隔符优先级 `"\n\n" → "\n" → "。" → "！" → "？" → "." → " "`，chunk_size=500, chunk_overlap=50
- **向量化**：GLM-Embedding-3 API，2048 维向量，批量 100 条/次
- **存储**：PostgreSQL pgvector，HNSW 索引 (vector_cosine_ops)

### 7. 短期/长期记忆

| 类型 | 存储 | 实现 |
|------|------|------|
| **短期** | Redis List | 滑动窗口 5 轮对话摘要，JwtAuthFilter 注入请求 |
| **长期** | PostgreSQL pgvector | 语义相似度检索用户历史对话，HNSW 加速 |

### 8. Agent Trace — 全链路可观测

每个请求生成 `TraceContext`，记录四阶段子 trace：

| 阶段 | 字段 |
|------|------|
| GateTrace | intent, rewritten_query, safety_tags, latency_ms |
| RetrievalTrace | rag_doc_count, memory_doc_count, reranked_top_n, latency_ms |
| GenerationTrace | model, token_count, latency_ms |
| VerificationTrace | passed, confidence, safety_violations, latency_ms |

后端关键日志（`[RAG]` 前缀）：
```
[RAG] GateKeeper: intent=simple, rewritten_query='高血压 症状 并发症', needs_rag=True, needs_memory=False
[RAG] Semantic: 15 docs, Keyword: 12 docs
[RAG] After RRF merge: 20 unique docs
[RAG] Reranked top docs: ['高血压临床指南(0.045)', 'WHO高血压防治(0.032)']
[RAG] Verification: passed=True, confidence=high, violations=[]
[RAG] Sending 5 sources: ['高血压临床指南', 'WHO高血压防治']
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Pinia + TypeScript + Vite |
| Java Gateway | Spring Boot 3 + MyBatis + Spring Security + JWT + BCrypt |
| Python Agent | FastAPI + SQLAlchemy + Pydantic Settings + httpx + Alembic |
| 向量数据库 | PostgreSQL 16 + pgvector (HNSW, cosine) |
| 关系数据库 | MySQL 8 (用户认证) |
| 缓存 | Redis 7 (短期记忆 + 限流 + Token 管理) |
| 消息队列 | RabbitMQ 3 (异步持久化) |
| LLM | OpenAI 兼容 API (DeepSeek-V4-Pro 主力 / Flash 路由+校验) |
| Embedding | GLM-Embedding-3 (2048 维) |
| 文本切片 | LangChain RecursiveCharacterTextSplitter |
| 依赖管理 | uv (Python) / npm (前端) / Maven (Java) |

## 项目结构

```
RAG_refactor/
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── api/                       # 后端 API 调用
│   │   │   ├── chat-python.ts         # Python Agent SSE 客户端
│   │   │   ├── chat-java.ts           # Java Gateway SSE 客户端
│   │   │   ├── knowledge.ts           # 知识库 CRUD
│   │   │   └── client.ts              # Axios 实例 (JWT 拦截器)
│   │   ├── components/
│   │   │   ├── chat-window.vue        # 聊天窗口 + Sources 引用展示
│   │   │   ├── knowledge-panel.vue    # 知识库管理面板
│   │   │   ├── session-list.vue       # 会话列表
│   │   │   ├── backend-switch.vue     # Python/Java 后端切换
│   │   │   └── login-bar.vue          # 登录栏
│   │   ├── stores/
│   │   │   └── chat.ts                # Pinia 状态 (双会话池 + 知识库)
│   │   ├── types/
│   │   │   ├── chat.ts                # 消息/会话/SSE 事件类型
│   │   │   └── api.ts                 # API 响应/SSE Chunk 类型
│   │   └── composables/               # 自动滚动 + Markdown 渲染
│   ├── vite.config.ts                 # Vite 代理配置
│   └── package.json
│
├── java-gateway/                      # Spring Boot 网关
│   └── src/main/java/com/rag/gateway/
│       ├── config/                    # Security + Redis + RabbitMQ + MySQL/PG 数据源
│       ├── controller/
│       │   ├── AuthController.java    # JWT 登录
│       │   ├── ChatController.java    # SSE 流式转发
│       │   └── ChatHistoryController.java  # 会话历史 CRUD
│       ├── filter/
│       │   ├── JwtAuthFilter.java     # JWT 验证 + Redis 短期记忆注入
│       │   └── RateLimitFilter.java   # Redis 滑动窗口限流
│       ├── mcp/
│       │   ├── MCPController.java     # MCP HTTP 端点 (/mcp/*)
│       │   ├── MemoryToolHandler.java  # 长期记忆 save/search
│       │   ├── AuditToolHandler.java   # 审计日志 + Trace 持久化
│       │   └── UserResourceHandler.java # 用户信息查询
│       ├── model/                     # ChatMessage, User, AgentTrace
│       ├── repository/
│       │   ├── mysql/UserMapper.java   # MySQL 用户查询
│       │   └── pg/                     # PostgreSQL: ChatMessage + Trace + Session
│       └── service/
│           ├── PythonAgentClient.java  # SSE 流式调用 Python Agent
│           ├── RedisService.java       # 短期记忆 + Token + 限流
│           └── AsyncWriteService.java  # Redis 滑动窗口追加
│
├── python-agent/                      # FastAPI Agent 核心
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口 + Alembic 自动迁移
│   │   ├── core/config.py             # Pydantic Settings (统一环境变量)
│   │   ├── api/v1/
│   │   │   ├── chat.py                # /v1/chat/completions (OpenAI 兼容)
│   │   │   └── knowledge.py           # /v1/knowledge/* (文档 CRUD)
│   │   ├── db/
│   │   │   ├── models.py              # SQLAlchemy ORM (ChatMessage, Knowledge*, AgentTrace)
│   │   │   ├── pgvector_client.py     # AsyncEngine + Session
│   │   │   └── vector_store.py        # 向量检索 + 文档管理 + LangChain 切片
│   │   ├── mcp/clients/
│   │   │   ├── memory_client.py       # 长期记忆检索 + 对话保存
│   │   │   ├── audit_client.py        # 审计日志上报
│   │   │   └── user_client.py         # 用户信息查询
│   │   └── services/
│   │       ├── agent_service.py       # Agent 编排器 (并行管道)
│   │       ├── gatekeeper_service.py  # 安全审核 + 意图分类 + 10 few-shot
│   │       ├── context_builder.py     # 医疗专用 Prompt 构建 (3 模板)
│   │       ├── llm_service.py         # LLM 流式调用
│   │       ├── embedding_service.py  # 向量嵌入 (mock/api, client 复用)
│   │       ├── reranker_service.py    # 交叉编码器重排 (mock/local/api)
│   │       ├── verification_service.py # 出口校验 (async)
│   │       ├── keyword_engine.py      # BM25 内存倒排索引
│   │       ├── trace_context.py       # Agent Trace 四阶段可观测
│   │       └── prompts/               # Jinja2 模板
│   │           ├── simple_qa.j2
│   │           ├── history_chat.j2
│   │           └── clarify.j2
│   ├── alembic/                       # 数据库迁移
│   │   ├── env.py                     # 异步引擎 + settings 读取 + autogenerate
│   │   └── versions/
│   │       ├── 001_init.py            # pgvector + 全表 + HNSW 索引
│   │       ├── 002_notnull_constraints.py
│   │       └── 543e5b7ec2eb_add_agent_traces_table.py
│   ├── pyproject.toml                 # uv 依赖声明 (唯一真相源)
│   ├── uv.lock                        # 锁定版本
│   └── Dockerfile                     # uv-based 构建
│
├── db/migrations/                     # Docker 首次启动 SQL
│   ├── 001_init.sql                   # CREATE EXTENSION vector
│   ├── 002_mysql_users.sql            # MySQL 用户表 + root 初始化
│   └── 003_mysql_chat_messages.sql    # MySQL 聊天记录表
│
├── docker-compose.yml                 # 全栈容器编排
├── .env                               # 环境变量
└── README.md
```

## 部署方式

### 方式一：Docker Compose 全栈部署（推荐）

```bash
# 1. 克隆项目
git clone git@github.com:Luminary3C/Reconstruction-of-medical-QA-system.git
cd RAG_refactor

# 2. 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件，必须配置：

```env
# LLM API（必须）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-llm-api.com/v1
LLM_MODEL=DeepSeek-V4-Pro
GATEKEEPER_MODEL=DeepSeek-V4-Flash
VERIFICATION_MODEL=DeepSeek-V4-Flash
RERANKER_MODEL=DeepSeek-V4-Flash

# 基础设施密码（建议修改默认值）
PG_PASSWORD=your-pg-password
MQ_PASSWORD=your-mq-password
JWT_SECRET=your-jwt-secret-in-production

# Embedding
EMBEDDING_MODE=api
EMBEDDING_MODEL=GLM-Embedding-3
```

```bash
# 3. 构建并启动所有服务
docker-compose up -d --build

# 4. 查看日志
docker-compose logs -f python-agent    # Agent 核心
docker-compose logs -f java-gateway   # Java 网关

# 5. 验证服务状态
curl http://localhost:8080/actuator/health   # Java 健康检查
curl http://localhost:8000/health           # Python 健康检查
```

服务端口映射：

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| PostgreSQL | 5432 | 5432 | pgvector 向量库 |
| MySQL | 3306 | 3307 | 用户认证 |
| Redis | 6379 | 6379 | 短期记忆 + 限流 |
| RabbitMQ | 5672/15672 | 5672/15672 | 异步队列/管理面板 |
| Java Gateway | 8080 | 8080 | API 网关 |
| Python Agent | 8000 | 8000 | Agent 核心 |

数据库表结构由 Alembic 自动管理，Python Agent 启动时自动执行 `alembic upgrade head`。

### 方式二：本地开发

#### 前置条件

- Python 3.11+
- Node.js 18+
- Java 17+ (Maven)
- uv (Python 包管理器)
- Docker (运行基础设施)

#### 1. 启动基础设施

```bash
# 仅启动 PG + Redis + RabbitMQ + MySQL
docker-compose up -d postgres redis rabbitmq

# 等待健康检查通过
docker-compose ps
```

#### 2. 启动 Python Agent

```bash
cd python-agent

# 安装依赖
uv sync

# 数据库迁移（首次或 schema 变更后）
uv run alembic upgrade head

# 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 启动 Java Gateway

```bash
cd java-gateway

# Maven 构建
./mvnw spring-boot:run

# 或使用 IDE 直接运行 GatewayApplication
```

#### 4. 启动前端

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:5173

Vite 代理配置：
- `/v1/*` → `http://localhost:8000` (Python Agent)
- `/api/v1/*` → `http://localhost:8080` (Java Gateway)

## 使用说明

### 双后端切换

前端支持 Python Agent 直连和 Java Gateway 两种后端：

| 模式 | 特点 |
|------|------|
| **Python** | 直连 Agent，无需登录，适合开发调试 |
| **Java** | 经过网关认证，支持用户体系、会话持久化、限流 |

### 管理员登录

Java Gateway 模式下，默认管理员账号：

| 字段 | 值 |
|------|------|
| 用户名 | `root` |
| 密码 | `root123` |

登录后可管理知识库（上传/删除文档）。

### 知识库管理

1. 切换到「知识库」标签页
2. 选择上传方式：文件上传（.txt/.pdf/.md/.docx）或文本粘贴
3. 填写标题和来源类型，点击上传
4. 文档自动完成：解析 → LangChain 递归切片 → GLM-Embedding-3 向量化 → pgvector 存储

### 对话示例

| 输入 | 意图 | 流程 |
|------|------|------|
| "高血压有什么症状" | simple | 乐观检索 → RRF → Rerank → 知识库回答 |
| "上次说的药叫什么" | history | 乐观检索 + 长期记忆 → Rerank → 历史关联回答 |
| "头疼" | clarify | 追问模板 → 引导补充症状细节 |
| "布洛芬吃几片" | reject | drug_dosage 模板 → 安全拒答 |
| "胸口剧痛喘不上气" | reject | emergency 模板 → 120 急诊提醒 |

回答下方会展示引用的知识库文档及相关度评分。

## 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API 地址 |
| `LLM_API_KEY` | (空) | LLM API Key |
| `LLM_MODEL` | `gpt-4o` | 主力生成模型 |
| `GATEKEEPER_MODEL` | (同 LLM_MODEL) | GateKeeper 路由模型 |
| `VERIFICATION_MODEL` | (同 LLM_MODEL) | 校验模型 |
| `GATEKEEPER_ENABLED` | `true` | 是否启用 GateKeeper |
| `VERIFICATION_ENABLED` | `true` | 是否启用出口校验 |
| `EMBEDDING_MODE` | `mock` | `mock` / `api` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_DIM` | `2048` | 向量维度 |
| `RERANKER_MODE` | `mock` | `mock` / `local` / `api` |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Reranker 模型 |
| `RERANKER_TOP_N` | `5` | Rerank 返回文档数 |
| `MCP_ENABLED` | `true` | 是否启用 MCP 客户端 |
| `JAVA_MCP_URL` | `http://localhost:8080/mcp` | Java MCP 端点 |
| `JWT_SECRET` | `changeme-in-production-use-env-var` | JWT 签名密钥 |
| `PG_PASSWORD` | `123456` | PostgreSQL 密码 |

## 数据库迁移

Python Agent 使用 Alembic 管理 PostgreSQL schema：

```bash
cd python-agent

# 查看当前版本
uv run alembic current

# 查看迁移历史
uv run alembic history

# 生成新迁移（修改 models.py 后）
uv run alembic revision --autogenerate -m "description"

# 执行迁移
uv run alembic upgrade head

# 回滚一步
uv run alembic downgrade -1
```

注意：HNSW 向量索引由 `include_object` 过滤，不在 autogenerate 中自动检测。新增向量索引需手动编写迁移。

## 仓库地址

```
git@github.com:Luminary3C/Reconstruction-of-medical-QA-system.git
```
