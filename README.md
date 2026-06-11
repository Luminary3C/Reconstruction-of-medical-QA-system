# 医疗问答系统重构 (Medical QA System Reconstruction)

基于 Agent 范式的医疗问答系统，采用 Java Gateway + Python Agent 双服务架构，实现安全审核、智能检索决策、流式生成与出口校验的分层 Agent 流程。

## 系统架构

```
┌──────────┐     SSE      ┌──────────────┐     HTTP/MCP     ┌──────────────┐
│  前端     │◄────────────►│  Java Gateway │◄───────────────►│ Python Agent │
│  Vue 3    │              │  Spring Boot  │                 │  FastAPI      │
└──────────┘              └───────┬───────┘                 └──────┬───────┘
                                  │                                │
                    ┌─────────────┼─────────────┐        ┌────────┼────────┐
                    │             │             │        │        │        │
               ┌────▼───┐  ┌─────▼────┐  ┌────▼───┐  ┌─▼──┐  ┌──▼──┐  ┌─▼───┐
               │ Redis  │  │ RabbitMQ │  │ MySQL  │  │PG   │  │ PG  │  │ LLM │
               │ 短期记忆│  │ 异步队列  │  │ 用户表 │  │向量库│  │审计 │  │ API │
               └────────┘  └──────────┘  └────────┘  └─────┘  └─────┘  └─────┘
```

## Agent 问答流程

```
用户问题
    ↓
[GateKeeper] 轻量LLM, 非stream — 安全审核 + 意图分类 + 查询改写
    ├── REJECT  → 返回安全提示（阻断，不走检索和生成）
    ├── CLARIFY → 返回追问模板（需要更多信息）
    ├── SIMPLE  → 仅走 RAG 检索
    └── HISTORY → RAG + 长期记忆检索
    ↓
[Selective Retrieval] 按意图选择性并发检索
    ├── RAG 知识库 (pgvector, top_k=20 → rerank → top_n=5)
    └── 长期记忆 (Java MCP → PG chat_messages)
    ↓
[Reranker] 交叉编码器精排 (mock / local / api)
    ↓
[Generation] 主力LLM 流式生成 + 医疗专用 system prompt
    ↓
[Verification] 同步出口校验 — 事实一致性 + 安全合规 + 置信度
    → 有风险 → SSE推送免责声明（红色 blockquote）
    → 无风险 → 直接关闭
    ↓
[Post-process] 异步: embedding持久化 + 审计日志 + trace上报
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Pinia + TypeScript + Vite |
| Java Gateway | Spring Boot 3 + MyBatis + Spring Security + JWT |
| Python Agent | FastAPI + SQLAlchemy + Pydantic + httpx |
| 向量数据库 | PostgreSQL + pgvector (IVFFlat, cosine) |
| 缓存 | Redis 7 |
| 消息队列 | RabbitMQ 3 |
| LLM | OpenAI API (可替换) |

## 项目结构

```
RAG_refactor/
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── api/              # Python/Java 后端 API 调用
│       ├── components/       # 聊天窗口、会话列表、登录栏
│       ├── stores/           # Pinia 状态管理（双会话池）
│       └── types/            # TypeScript 类型定义
├── java-gateway/             # Spring Boot 网关
│   └── src/main/java/com/rag/gateway/
│       ├── config/           # Security、CORS 配置
│       ├── controller/       # REST 控制器
│       ├── mcp/              # MCP Tool Handler (Memory/Audit/User)
│       ├── model/            # 数据模型 (ChatMessage, User, AgentTrace)
│       ├── repository/       # MyBatis Mapper (MySQL + PG)
│       └── service/          # 业务逻辑 + MQ 异步持久化
├── python-agent/             # FastAPI Agent 核心
│   └── app/
│       ├── api/v1/           # 路由: chat, knowledge
│       ├── db/               # pgvector 连接 + VectorStore
│       ├── mcp/clients/      # MCP HTTP 客户端 (memory/audit/user)
│       ├── services/         # 核心服务
│       │   ├── agent_service.py       # Agent 编排器
│       │   ├── gatekeeper_service.py  # 安全审核 + 意图分类
│       │   ├── context_builder.py     # 医疗专用 prompt 构建
│       │   ├── llm_service.py         # LLM 流式调用
│       │   ├── embedding_service.py   # 向量嵌入 (mock/api)
│       │   ├── reranker_service.py    # 交叉编码器重排
│       │   ├── verification_service.py # 出口校验
│       │   └── trace_context.py       # Agent Trace 可观测性
│       └── core/config.py    # Pydantic Settings
├── db/migrations/            # 数据库迁移脚本
│   ├── 001_init.sql          # PG 初始化 + pgvector 扩展
│   ├── 002_mysql_users.sql   # MySQL 用户表
│   ├── 003_mysql_chat_messages.sql
│   ├── 004_knowledge_tables.sql  # 知识库 + 向量索引
│   └── 005_agent_traces.sql      # Agent 审计追踪
├── docker-compose.yml        # 全栈容器编排
└── .env                      # 环境变量
```

## Agent 核心模块

### GateKeeper — 安全审核 + 意图分类 + 查询改写

单次轻量 LLM 调用，返回结构化 JSON：
- `intent`: simple / history / clarify / reject
- `safety_tags`: 危险标签（如 drug_recommendation, diagnosis）
- `needs_rag` / `needs_memory`: 检索决策
- `rewritten_query`: 指代消解后的改写查询

### Reranker — 交叉编码器精排

粗检索 top_k=20 → 精排 top_n=5，三种模式：
- `mock`: 0.7×similarity + 0.3×keyword_overlap
- `local`: sentence-transformers CrossEncoder (BAAI/bge-reranker-v2-m3)
- `api`: 外部服务 (Cohere/Jina)

### Verification — 出口校验

流式输出结束后同步执行，LLM 审查三项：
1. 事实一致性 — 回答是否与知识库文档矛盾
2. 安全合规 — 是否推荐用药/给出诊断/遗漏免责声明
3. 置信度评估 — high / medium / low

校验结果通过 SSE `verification` 事件推送到前端，低置信度时追加红色免责声明。

### Agent Trace — 全链路可观测

每个请求生成 `TraceContext`，记录四阶段子 trace：
- `GateTrace`: intent, rewritten_query, latency_ms
- `RetrievalTrace`: doc_count, reranked_top_n, latency_ms
- `GenerationTrace`: model, token_count, latency_ms
- `VerificationTrace`: passed, confidence, violations, latency_ms

Trace 通过 `agent_trace` 事件经 MCP 审计链路持久化到 PG `agent_traces` 表。

## 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY 等

# 2. 启动基础设施 + 服务
docker-compose up -d

# 3. 前端开发
cd frontend
npm install
npm run dev
```

## 仓库地址

```
git@github.com:Luminary3C/Reconstruction-of-medical-QA-system.git
```
