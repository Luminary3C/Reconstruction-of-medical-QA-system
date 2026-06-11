# Tasks: MCP Plugin Architecture

## Phase 1: 基础设施 (Foundation)

- [x] **T1**: 搭建 Retrieval MCP Server (Python, stdio transport)
  - 实现 `search_knowledge_base` Tool
  - 对接向量数据库 (Milvus/Qdrant)
  - 实现 `list_knowledge_sources` Tool
  - 单测: Tool 调用返回正确向量检索结果

- [x] **T2**: Python Agent 集成 MCP Client
  - 使用 `mcp` Python SDK 初始化 Client
  - 封装 `RetrievalMCPClient` (stdio transport)
  - 灵敏度开关: `MCP_ENABLED=true/false` 环境变量切换
  - 单测: Client 调用 Tool 端到端

- [x] **T3**: 搭建 Java MCP Server 基础框架
  - 引入 SpringBoot MCP Server starter
  - 配置 HTTP transport endpoint (`/mcp`)
  - 实现 Memory / User / Audit 三个 Server 的空壳与注册

## Phase 2: 核心能力迁移 (Core Migration)

- [x] **T4**: Memory MCP Server — 实现 `search_long_term_memory`
  - pgvector 查询: embedding → 向量检索
  - 返回结果压缩 (只返回摘要, 不返回原文)
  - 单测: pgvector Docker 集成测试

- [x] **T5**: Memory MCP Server — 实现 `save_conversation`
  - 写 RabbitMQ → MyBatis → pgvector 链路
  - 异步 fire & forget, 不阻塞 Agent
  - 单测: 消息写入 MQ 验证

- [x] **T6**: User MCP Server — 实现 Resources
  - `user://{user_id}/profile` Resource
  - `user://{user_id}/permissions` Resource
  - 单测: Resource 读取验证

- [x] **T7**: Audit MCP Server — 实现 `audit_log` Tool
  - Kafka 生产者写入审计事件
  - 单测: 事件写入 Kafka topic

## Phase 3: Agent 改造 (Agent Refactor)

- [x] **T8**: Python Agent 决策循环改造
  - 移除硬编码的 VectorDB/Java HTTP 调用
  - 统一改用 MCP Client 调用 Tool
  - 三路召回: short-term(请求头) + knowledge_base(MCP) + long_term(MCP)
  - 集成测试: 端到端问答链路

- [x] **T9**: Agent prompt 动态 Tool 感知
  - Agent 启动时自动发现所有 MCP Tool
  - 将 Tool 列表注入 system prompt
  - 测试: 新增 Tool 后 Agent 自动感知

## Phase 4: 测试与部署 (Test & Deploy)

- [x] **T10**: Docker Compose 集成部署配置
  - PostgreSQL (pgvector, 5432:5432)
  - Redis (6379:6379)
  - Java Gateway (8080:8080, 内嵌 MCP Servers)
  - Python Agent (8000:8000, 内嵌 Retrieval MCP Server)
  - 健康检查 + 启动顺序

- [x] **T11**: 端到端集成测试
  - 测试场景: 用户提问 → 三路召回 → LLM 回答 → 持久化 → 审计
  - 测试 MCP Tool timeout 降级
  - 测试 Retrieval Server 崩溃恢复

- [x] **T12**: 删除旧硬编码调用代码
  - 清理 Agent 中旧的 VectorDB 直接调用
  - 清理 Agent 中旧的 Java HTTP 调用
  - 确保无遗留硬编码路径