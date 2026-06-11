# Tasks: Agent Quality Loop

## Phase 1: Query Rewrite (合并到 GateKeeper)

- [ ] T1: 扩展 `GateResult` 模型，新增 `rewritten_query` 字段
- [ ] T2: 扩展 `GATE_SYSTEM_PROMPT`，追加 query rewrite 指令
- [ ] T3: 修改 `agent_service.py`，检索时使用 `gate.rewritten_query` 替代原始 query
- [ ] T4: 修改 `VectorStore.search()` 默认 top_k 从 5 改为 20（粗排多取）
- [ ] T5: 修改 `MemoryMCPClient.search_long_term_memory()` top_k 参数改为 20

## Phase 2: Reranker (交叉编码器)

- [ ] T6: 新建 `app/services/reranker_service.py` — RerankerService（mock/local/api 三模式）
- [ ] T7: 实现 mock reranker：基于 similarity + keyword overlap 加权
- [ ] T8: 实现本地部署 reranker：sentence-transformers + bge-reranker-v2-m3
- [ ] T9: 修改 `agent_service.py`，检索后调用 reranker 精排
- [ ] T10: 修改 `config.py`，新增 reranker_mode / reranker_model / reranker_top_n / retrieval_coarse_top_k

## Phase 3: Verification (出口校验)

- [ ] T11: 新建 `app/services/verification_service.py` — VerificationService + VerificationResult
- [ ] T12: 设计 Verification prompt（事实一致性 + 安全合规 + 置信度评估）
- [ ] T13: 修改 `agent_service._post_process()`，异步调用 verification
- [ ] T14: 修改 `config.py`，新增 verification_enabled / verification_model

## Phase 4: Agent Trace (可观测性)

- [ ] T15: 新建 `app/services/trace_context.py` — TraceContext + GateTrace + RetrievalTrace + GenerationTrace + VerificationTrace
- [ ] T16: 修改 `agent_service.py`，全链路填充 TraceContext 字段，计时各阶段 latency_ms
- [ ] T17: 新建 `db/migrations/005_agent_traces.sql` — PG agent_traces 表
- [ ] T18: 新建 `java-gateway/.../model/AgentTrace.java` — Trace DO
- [ ] T19: 新建 `java-gateway/.../repository/pg/TraceMapper.java` — MyBatis mapper
- [ ] T20: 修改 `java-gateway/.../mcp/AuditToolHandler.java` — agent_trace 事件持久化到 PG
- [ ] T21: 修改 `audit_client.py` — 增加 trace 上报方法

## Phase 5: 集成验证

- [ ] T22: 测试完整链路：提问 → gate+rewrite → retrieval → rerank → generate → verify → trace
- [ ] T23: 验证 PG `agent_traces` 表写入正确
- [ ] T24: 验证 mock reranker 的精排效果