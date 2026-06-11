# Proposal: Agent Quality Loop

## Summary

为 Python Agent 增加四个质量增强模块——查询改写、交叉编码器 Reranker、出口校验（Verification）、Agent Trace（全链路可观测性）——构成"入口审核→检索增强→生成→出口校验→审计追溯"的完整闭环。

## Motivation

当前 Agent 存在三个质量短板：

1. **指代性 query 检索命中率低** — 用户说"刚才说的那个降压药"，向量检索与原文语义距离远，长期记忆召回失效
2. **粗排噪声多** — pgvector cosine similarity 是粗排，相似≠相关，top_k 中常有低相关度文档
3. **出口无校验** — 入口有 GateKeeper 审核，但生成后无人检查回答是否与知识库矛盾、是否违反安全规则
4. **决策不可追溯** — 审计只记简单 event_type，无法回溯完整的 intent→retrieval→generation→verification 链路

## Scope

### In scope

1. **Query Rewrite** — 合并到 GateKeeper LLM 调用，输出 `rewritten_query` 字段
2. **Reranker** — 交叉编码器（cross-encoder）模型，对 RAG 和长期记忆的粗排结果精排
3. **Verification** — 流式生成结束后异步 LLM 校验（事实一致性 + 安全合规 + 置信度评估）
4. **Agent Trace** — Python 侧生成 TraceContext 结构化对象，通过 MCP 上报；Java 侧持久化到 PG `agent_traces` 表

### Non-goals

- 实时拦截不安全回答（Verification 是事后审计式，不修改已输出内容）
- 自研 cross-encoder 模型（使用开源预训练模型或 API 服务）
- LLM Function Calling 工具自主调用（后续 change 覆盖）
- Elasticsearch / Kafka 替换 audit 存储（MVP 用 PG 表）

## Impact

### Python Agent

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/services/gatekeeper_service.py` | 修改 | 扩展 prompt + 输出结构，新增 `rewritten_query` 字段 |
| `app/services/reranker_service.py` | 新建 | 交叉编码器精排服务 |
| `app/services/verification_service.py` | 新建 | 出口校验 LLM 服务 |
| `app/services/trace_context.py` | 新建 | TraceContext 结构化对象 |
| `app/services/agent_service.py` | 重写 | 整合 rewrite→rerank→verify→trace 全链路 |
| `app/db/vector_store.py` | 修改 | search() 默认多取（粗排 top_k=20），等 reranker 精排 |
| `app/mcp/clients/memory_client.py` | 修改 | search 返回更多结果供 reranker 精排 |
| `app/core/config.py` | 修改 | 新增 reranker/verification 配置项 |

### Java Gateway

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/mcp/AuditToolHandler.java` | 修改 | 从 log.info → 持久化到 PG `agent_traces` 表 |
| `app/repository/pg/TraceMapper.java` | 新建 | agent_traces 表的 MyBatis mapper |
| `app/model/AgentTrace.java` | 新建 | Trace DO |

### Database

| 文件 | 操作 | 说明 |
|------|------|------|
| `db/migrations/005_agent_traces.sql` | 新建 | `agent_traces` 表 |

## Dependencies

- Cross-encoder 模型：优先考虑本地部署 `bge-reranker-v2-m3`（多语言），或 mock 实现待后续切换
- 当前 GateKeeper + EmbeddingService + VectorStore + MemoryMCPClient 基础设施