# Design: MCP Plugin Architecture

## Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │           Client (Browser)          │
                        └────────────────┬────────────────────┘
                                         │ JWT + SSE
                                         ▼
                        ┌─────────────────────────────────────┐
                        │   Java SpringBoot (API Gateway)     │
                        │                                     │
                        │  ┌─────────────┐  ┌──────────────┐  │
                        │  │ Auth Filter │  │ SSE Relay    │  │
                        │  │ + Redis     │  │ + StringBuilder│ │
                        │  │   short-term│  │   accumulate │  │
                        │  └─────────────┘  └──────────────┘  │
                        └────────┬───────────────┬────────────┘
                                 │               │
                    HTTP stream  │               │ MCP (JSON-RPC)
                    (短期上下文    │               │
                     放入请求头)   │               │
                                 ▼               ▼
┌────────────────────────────────┐  ┌──────────────────────────┐
│   Python Agent (MCP Client)    │  │  MCP Server Cluster      │
│                                │  │                          │
│   ┌────────────────────────┐   │  │  ┌────────────────────┐  │
│   │  Agent Decision Loop    │   │  │  │ Retrieval Server   │  │
│   │                        │   │  │  │ (Python, localhost) │  │
│   │  1. Parse user query   │   │  │  │                    │  │
│   │  2. Parallel MCP call: │   │  │  │  Tools:            │  │
│   │     - search_knowledge │───┼──┼──│  - search_knowledge│  │
│   │     - search_long_term │───┼──┼──│    _base           │  │
│   │  3. Fuse context       │   │  │  │                    │  │
│   │  4. LLM stream (direct)│   │  │  │  Backend: VectorDB  │  │
│   │  5. save_conversation  │───┼──┼──│  (Milvus/Qdrant)   │  │
│   │     (fire & forget)    │   │  │  └────────────────────┘  │
│   │  6. audit_log          │───┼──┼──┐                       │
│   └────────────────────────┘   │  │  │  ┌────────────────────┐
│                                │  │  ├──│ Memory Server      │
│   MCP Transport:               │  │  │  │ (Java, SpringBoot) │
│   - Retrieval → stdio          │  │  │  │                    │
│   - Others    → HTTP           │  │  │  │  Tools:            │
│                                │  │  │  │  - search_long_term│
└────────────────────────────────┘  │  │  │  - save_conversation│
                                    │  │  │                    │
                                    │  │  │  Backend: pgvector │
                                    │  │  └────────────────────┘
                                    │  │  ┌────────────────────┐
                                    │  ├──│ User Server        │
                                    │  │  │ (Java, SpringBoot) │
                                    │  │  │                    │
                                    │  │  │  Resources:        │
                                    │  │  │  - user_profile    │
                                    │  │  │  - user_permissions│
                                    │  │  │                    │
                                    │  │  │  Backend: User DB  │
                                    │  │  └────────────────────┘
                                    │  │  ┌────────────────────┐
                                    │  └──│ Audit Server       │
                                    │     │ (Java, SpringBoot) │
                                    │     │                    │
                                    │     │  Tools:            │
                                    │     │  - audit_log       │
                                    │     │                    │
                                    │     │  Backend: Kafka    │
                                    │     └────────────────────┘
                                    └──────────────────────────┘
```

## MCP Server Specifications

### 1. 检索 MCP Server (Python)

| 属性 | 值 |
|------|-----|
| 语言 | Python |
| 传输方式 | stdio (同进程部署, 零网络开销) |
| 部署位置 | 与 Agent 同 Pod/K8s sidecar |

**Tools:**

| Tool | 参数 | 返回 | 说明 |
|------|------|------|------|
| `search_knowledge_base` | `query: str, top_k: int = 5, filters: dict = None` | `List[{chunk_id, content, score, metadata}]` | 知识库向量检索 |
| `list_knowledge_sources` | — | `List[{source_id, name, doc_count}]` | 列出可用知识库 |

### 2. 记忆 MCP Server (Java)

| 属性 | 值 |
|------|-----|
| 语言 | Java |
| 传输方式 | HTTP (SpringBoot 内嵌 MCP endpoint) |
| 部署位置 | Java API Gateway 同进程 |

**Tools:**

| Tool | 参数 | 返回 | 说明 |
|------|------|------|------|
| `search_long_term_memory` | `query: str, user_id: str, top_k: int = 10` | `List[{memory_id, content, score, timestamp}]` | pgvector 长期记忆检索 |
| `save_conversation` | `user_id: str, question: str, answer: str, metadata: dict` | `{conversation_id}` | 异步持久化对话 |
| `summarize_history` | `user_id: str, window: str = "7d"` | `{summary: str}` | 压缩历史对话摘要 |

### 3. 用户 MCP Server (Java)

| 属性 | 值 |
|------|-----|
| 语言 | Java |
| 传输方式 | HTTP |
| 部署位置 | Java API Gateway 同进程 |

**Resources:**

| Resource | URI 模式 | 返回 | 说明 |
|----------|----------|------|------|
| User Profile | `user://{user_id}/profile` | `{name, preferences, plan}` | 用户基础信息 |
| User Permissions | `user://{user_id}/permissions` | `{roles, scopes}` | 权限列表 |

### 4. 审计 MCP Server (Java)

| 属性 | 值 |
|------|-----|
| 语言 | Java |
| 传输方式 | HTTP |
| 部署位置 | Java API Gateway 同进程 |

**Tools:**

| Tool | 参数 | 返回 | 说明 |
|------|------|------|------|
| `audit_log` | `event_type: str, user_id: str, detail: dict` | `{ack: bool}` | 审计事件写入 (fire & forget) |

## Transport Strategy

```
┌─────────────────────────────────────────────────────┐
│  Transport Selection Rationale                       │
├──────────────┬──────────┬───────────────────────────┤
│ Server       │ Transport│ Why                       │
├──────────────┼──────────┼───────────────────────────┤
│ Retrieval    │ stdio    │ 热路径, 与 Agent 同进程,   │
│              │          │ 零网络延迟, 向量检索本来就 │
│              │          │ 需要几十ms, JSON-RPC 可忽略│
├──────────────┼──────────┼───────────────────────────┤
│ Memory       │ HTTP     │ Java 侧, 已有 SpringBoot,  │
│              │          │ 跨语言走 HTTP 最自然       │
├──────────────┼──────────┼───────────────────────────┤
│ User         │ HTTP     │ 同上, 复用 Java Gateway    │
├──────────────┼──────────┼───────────────────────────┤
│ Audit        │ HTTP     │ fire & forget, 低优先级    │
└──────────────┴──────────┴───────────────────────────┘
```

## Agent Decision Loop (MCP-ified)

```python
async def agent_loop(user_query: str, user_id: str, short_term_ctx: list):
    # 1. 并行 MCP Tool 调用
    rag_docs, long_term_mems = await asyncio.gather(
        retrieval_client.call_tool("search_knowledge_base", {"query": user_query}),
        memory_client.call_tool("search_long_term_memory", {"query": user_query, "user_id": user_id}),
    )

    # 2. 上下文融合 (短期上下文已由 Java 放入请求头, 无需 MCP 调用)
    fused_context = build_context(short_term_ctx, rag_docs, long_term_mems)

    # 3. LLM 推理 (直接 HTTP streaming, 不走 MCP)
    response = await llm_stream(fused_context, user_query)

    # 4. 异步写回 (fire & forget)
    asyncio.ensure_future(
        memory_client.call_tool("save_conversation", {
            "user_id": user_id,
            "question": user_query,
            "answer": response,
        })
    )
    asyncio.ensure_future(
        audit_client.call_tool("audit_log", {
            "event_type": "chat_completion",
            "user_id": user_id,
            "detail": {"query": user_query, "context_sources": ...},
        })
    )

    return response  # streaming
```

## Infrastructure (Docker)

```yaml
# docker-compose.yml 核心服务
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  java-gateway:
    build: ./java-gateway
    ports: ["8080:8080"]
    # 内嵌 Memory/User/Audit MCP Server (HTTP)

  python-agent:
    build: ./python-agent
    ports: ["8000:8000"]
    # 内嵌 MCP Client + Retrieval MCP Server (stdio)
```

## Risk Mitigation

| 风险 | 应对 |
|------|------|
| MCP Tool 调用超时阻塞 Agent 循环 | 所有 Tool 设置 500ms timeout, 超时降级返回空结果 |
| Retrieval Server 进程崩溃 | Agent 启动时 spawn Retrieval Server, 崩溃后自动重启 |
| JSON-RPC 序列化大向量结果 | 返回 top_k 数量限制, 单次最多 20 条 |
| MCP Server 版本不兼容 | 使用 MCP 协议内置的 `initialize` 协商能力 |