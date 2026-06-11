# Design: Agent Quality Loop

## Architecture Overview

```
用户问题
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ GateKeeper + QueryRewrite (一次 LLM 调用)                │
│  intent=simple/history/clarify/reject                    │
│  rewritten_query: 口语化/指代性 → 独立可检索的完整 query  │
└────────────────────┬────────────────────────────────────┘
                     │ rewritten_query
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Selective Retrieval (按意图选择检索路径)                   │
│  RAG:    vector_store.search(rewritten_query, top_k=20)  │
│  Memory: memory.search(rewritten_query, user_id, top=20) │
└────────────────────┬────────────────────────────────────┘
                     │ 粗排结果 (多取)
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Reranker (交叉编码器精排)                                 │
│  rag_docs:  20 → 5                                      │
│  memories:  20 → 3                                      │
│  延迟: ~100-300ms                                        │
└────────────────────┬────────────────────────────────────┘
                     │ 精排结果
                     ▼
┌─────────────────────────────────────────────────────────┐
│ ContextBuilder + LLM Generation (流式输出)                │
│  system prompt: 医疗安全规则 + 免责声明                    │
└────────────────────┬────────────────────────────────────┘
                     │ full_answer
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Verification (异步 LLM 校验，不影响流式体验)               │
│  fact_check:  回答与知识库是否一致                         │
│  safety_check: 是否违反医疗安全规则                        │
│  confidence:   high / medium / low                       │
│  延迟: ~300-800ms (异步执行)                              │
└────────────────────┬────────────────────────────────────┘
                     │ verification result
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Post-process                                             │
│  1. embedding write-back → PG                            │
│  2. trace → audit MCP → Java → PG agent_traces 表        │
└─────────────────────────────────────────────────────────┘
```

## Module 1: Query Rewrite (合并到 GateKeeper)

### 设计决策

**不单独创建服务，而是扩展 GateKeeper 的 prompt 和输出结构。**

理由：
- GateKeeper 已经做了一次 LLM 调用，改写和意图分类在同一次推理中完成
- 零额外延迟
- history intent 需要指代消解（重改写），simple intent 需要口语化修正（轻改写），两者在同一个 prompt 中自然处理

### 扩展后的 GateResult

```python
class GateResult(BaseModel):
    intent: str                    # simple / history / clarify / reject
    reason: str = ""
    safety_tags: list[str] = []
    needs_rag: bool = True
    needs_memory: bool = False
    rewritten_query: str = ""      # 🔥 新增
```

### Prompt 扩展

在现有 GATE_SYSTEM_PROMPT 末尾追加：

```
4. QUERY REWRITE:
   - Rewrite the user's question into a self-contained, search-optimized query.
   - For intent=history: resolve all references to previous conversations.
     Example: "刚才说的那个降压药" → "ACEI类降压药物名称推荐"
   - For intent=simple: make the query more precise and search-friendly.
     Example: "头疼怎么办" → "头痛 常见病因 治疗方法 就诊建议"
   - For intent=clarify/reject: set rewritten_query to the original question.

Include "rewritten_query" in your JSON output.
```

### 使用方式

在 `agent_service.py` 中，检索时用 `gate.rewritten_query` 替代原始 `user_message`：

```python
retrieval_query = gate.rewritten_query or user_message
rag_docs = await self.vector_store.search(retrieval_query, top_k=20)
```

## Module 2: Reranker (交叉编码器)

### 架构

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ VectorStore  │     │ RerankerService  │     │ ContextBuilder│
│ search       │────▶│ rerank()         │────▶│ build()      │
│ top_k=20     │     │ → top_n=5        │     │              │
│ (粗排)       │     │ (精排)           │     │              │
└──────────────┘     └──────────────────┘     └──────────────┘
```

### RerankerService 实现

```python
class RerankerService:
    """Cross-encoder reranker — refines coarse retrieval results."""

    async def rerank(
        self, query: str, documents: list[dict], top_n: int = 5,
        content_key: str = "content",
    ) -> list[dict]:
        """
        Re-rank documents using cross-encoder scoring.
        Returns top_n documents sorted by relevance score.
        """
```

### Cross-encoder 方案

| 方案 | 模型 | 延迟 | 依赖 |
|------|------|------|------|
| **本地部署** | `BAAI/bge-reranker-v2-m3` (多语言, 568M) | ~100-300ms | `sentence-transformers`, GPU 可选 |
| **API 服务** | Cohere Rerank / Jina Rerank | ~200ms | API key, 网络调用 |
| **Mock** | 基于 similarity + keyword 加权 | <5ms | 无 |

**实现策略**：与 EmbeddingService 同理——支持 `RERANKER_MODE=mock|local|api`，当前默认 mock，后续切换。

Mock reranker 的 scoring 策略：
```python
def _mock_score(self, query: str, doc_content: str, semantic_score: float) -> float:
    # 1. semantic_score (来自 pgvector cosine similarity)
    # 2. keyword_overlap = len(set(jieba.cut(query)) & set(jieba.cut(doc_content))) / len(set(jieba.cut(query)))
    # 3. final = 0.7 * semantic_score + 0.3 * keyword_overlap
```

### VectorStore 改动

`search()` 新增参数 `top_k`，默认值从 5 改为 20（粗排多取），由 Reranker 精排到 5。

### 长期记忆也走 Reranker

`MemoryMCPClient` 返回的记忆片段同样经过 `RerankerService.rerank()` 精排，统一入口。

## Module 3: Verification (出口校验)

### 设计决策

**审计式而非拦截式** — 不修改已流式输出的回答，校验结果写入 trace。

理由：
- 用户已等完整个流式输出，实时拦截体验差
- system prompt 中已有安全规则（预防式），Verification 是二次确认
- 校验结果用于合规审计和后台告警，不改变前端展示

### VerificationService

```python
class VerificationResult(BaseModel):
    passed: bool = True
    safety_violations: list[str] = []
    confidence: str = "high"         # high / medium / low
    warnings: list[str] = []
    reason: str = ""

class VerificationService:
    """Post-generation answer verification — audit mode."""

    async def verify(
        self,
        answer: str,
        query: str,
        rag_docs: list[dict],
    ) -> VerificationResult:
```

### Verification Prompt

```
You are a medical answer verification system. Review the AI-generated answer for:

1. FACTUAL CONSISTENCY: Does the answer contradict any knowledge base documents provided?
2. SAFETY COMPLIANCE: Does the answer:
   - Recommend specific drug dosages?
   - Provide definitive diagnosis conclusions?
   - Omit necessary disclaimers?
3. CONFIDENCE ASSESSMENT: Based on the knowledge base coverage:
   - "high": Multiple sources agree, comprehensive coverage
   - "medium": Some sources support, but coverage is incomplete
   - "low": No direct sources, or conflicting information

Return JSON:
{"passed": true/false, "safety_violations": [...], "confidence": "high|medium|low", "warnings": [...], "reason": "..."}
```

### 调用时机

在 `agent_service._post_process()` 中，流式输出结束后异步执行：

```python
async def _post_process(self, gate, user_id, session_id, question, answer, rag_docs, trace):
    # 1. Verification
    verification = await self.verification.verify(answer, question, rag_docs)
    trace.verification = verification

    # 2. Embedding write-back
    ...

    # 3. Trace audit
    await self.audit.audit_log("agent_trace", user_id, trace.to_dict())
```

## Module 4: Agent Trace (可观测性)

### TraceContext 数据结构

```python
class GateTrace(BaseModel):
    intent: str
    reason: str
    rewritten_query: str
    safety_tags: list[str]
    latency_ms: int = 0

class RetrievalTrace(BaseModel):
    query_used: str = ""
    rag_results_count: int = 0
    rag_top_similarities: list[float] = []
    rag_latency_ms: int = 0
    memory_triggered: bool = False
    memory_results_count: int = 0
    memory_latency_ms: int = 0
    rerank_input_count: int = 0
    rerank_output_count: int = 0
    rerank_latency_ms: int = 0

class GenerationTrace(BaseModel):
    model: str = ""
    answer_length: int = 0
    latency_ms: int = 0

class VerificationTrace(BaseModel):
    passed: bool = True
    confidence: str = "high"
    safety_violations: list[str] = []
    warnings: list[str] = []
    latency_ms: int = 0

class TraceContext(BaseModel):
    trace_id: str
    user_id: str
    session_id: str
    created_at: str = ""
    gate: GateTrace = GateTrace(intent="", reason="", rewritten_query="", safety_tags=[])
    retrieval: RetrievalTrace = RetrievalTrace()
    generation: GenerationTrace = GenerationTrace()
    verification: VerificationTrace = VerificationTrace()
    persistence_redis_ok: bool = False
    persistence_pg_ok: bool = False
```

### PG agent_traces 表

```sql
CREATE TABLE agent_traces (
    id          BIGSERIAL PRIMARY KEY,
    trace_id    VARCHAR(64) NOT NULL UNIQUE,
    user_id     VARCHAR(100) NOT NULL,
    session_id  VARCHAR(100),
    gate_json   JSONB,
    retrieval_json   JSONB,
    generation_json  JSONB,
    verification_json JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_traces_user ON agent_traces(user_id);
CREATE INDEX idx_traces_session ON agent_traces(session_id);
CREATE INDEX idx_traces_created ON agent_traces(created_at);
```

使用 JSONB 存储 trace 子结构，避免频繁的 schema 变更，同时支持 PostgreSQL 的 JSON 查询能力。

### Java 侧改动

**AuditToolHandler** — 当 `event_type=agent_trace` 时，解析 detail 并 INSERT 到 `agent_traces` 表：

```java
public ApiResponse<?> auditLog(Map<String, Object> body) {
    String eventType = (String) body.get("event_type");

    if ("agent_trace".equals(eventType)) {
        // 持久化到 agent_traces 表
        traceMapper.insert(buildTrace(body));
    } else {
        // 原有逻辑: log.info
        log.info("AUDIT [{}] user={} detail={}", eventType, userId, detail);
    }
    ...
}
```

## 完整数据流 (带 Trace)

```
用户: "刚才说的那个降压药副作用有哪些"
    │
    │  trace = TraceContext(trace_id=uuid)
    ▼
[GateKeeper + QueryRewrite]  ── 1 次 LLM (~200ms)
    │  intent=history
    │  rewritten_query="ACEI类降压药物副作用"
    │  trace.gate = {intent, reason, rewritten_query, latency_ms}
    │
    ▼
[Selective Retrieval]
    │  rag: search(rewritten_query, top_k=20)       ~120ms
    │  memory: search(rewritten_query, user_id, 20)  ~350ms
    │  trace.retrieval = {rag_results_count, memory_results_count, ...}
    │
    ▼
[Reranker]  ── cross-encoder (~150ms)
    │  rag: 20 → 5
    │  memory: 20 → 3
    │  trace.retrieval.rerank_*
    │
    ▼
[ContextBuilder + LLM]  ── 流式输出 (~2000ms)
    │  trace.generation = {model, answer_length, latency_ms}
    │
    ▼
[Verification]  ── 异步 LLM (~500ms)
    │  fact_check ✓, safety_check ✓, confidence=medium
    │  trace.verification = {passed, confidence, ...}
    │
    ▼
[Post-process]
    │  embedding write-back → PG
    │  audit_log("agent_trace", trace.to_dict()) → Java MCP → PG agent_traces
    │
    ▼
trace_id=abc-123 全链路可追溯 ✓
```

**新增 LLM 调用统计**：
- GateKeeper + QueryRewrite: 1 次（与原来相同，扩展了 prompt）
- Verification: 1 次（新增，异步执行，不影响流式体验）
- Reranker: 0 次 LLM（cross-encoder 是独立模型推理，非 generative LLM）

## Config 新增

```python
# python-agent/app/core/config.py

# Reranker
reranker_mode: str = "mock"          # mock / local / api
reranker_model: str = "BAAI/bge-reranker-v2-m3"
reranker_top_n: int = 5              # 精排保留数量
retrieval_coarse_top_k: int = 20     # 粗排多取数量

# Verification
verification_enabled: bool = True
verification_model: str = ""          # 留空则用主模型
```

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| GateKeeper prompt 变长导致延迟增加 | 改写是轻量扩展，token 增量 <100，延迟影响 <50ms |
| Cross-encoder 本地部署需要 GPU | Mock 模式下用 rule-based 替代；CPU 推理 bge-reranker-v2-m3 也可运行（~300ms） |
| Verification 异步失败导致 trace 不完整 | Verification 失败时写入默认值 `{passed: true, confidence: "unknown"}` |
| agent_traces 表数据量增长 | 按月分区 + 30 天后归档 |