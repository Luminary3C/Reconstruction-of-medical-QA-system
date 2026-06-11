# Proposal: MCP Plugin Architecture

## Summary

将 Python Agent 的三路召回、记忆持久化、用户查询、审核日志等能力设计为 MCP (Model Context Protocol) 插件体系，实现 Agent 推理核心与基础设施的彻底解耦。

## Motivation

当前架构中 Python Agent 对 Redis、VectorDB、Java 服务的调用是硬编码的。每新增一个召回源或外部能力，都需要改 Agent 核心代码。MCP 插件化后：

- **新增召回源** = 实现一个 MCP Tool，Agent 零改动
- **切换向量引擎** = 替换 MCP Server 底层实现，接口不变
- **独立迭代** = 每个 MCP Server 可独立部署、扩缩、灰度

## Scope

### In scope
- Python Agent 内置 MCP Client，通过 Tool 调用基础设施
- 检索 MCP Server (Python): `search_knowledge_base`, 对接向量库
- 记忆 MCP Server (Java): `search_long_term_memory`, `save_conversation`
- 用户 MCP Server (Java): `get_user_profile`, `check_permission` (Resources)
- 审计 MCP Server (Java): `audit_log` (fire & forget)

### Non-goals
- LLM 推理的流式传输不走 MCP（性能敏感热路径）
- Redis 短期上下文不走 MCP（Java 鉴权阶段已拉取，请求头传入）
- SSE 透明传输不走 MCP（纯传输层）
- 不替换已有的 Java→Python HTTP 流式转发通道

## Impact

- **Agent 代码简化**: 移除硬编码的 VectorDB/Java 调用，统一为 `mcp_client.call_tool()`
- **新增能力**: 动态 Tool 发现，Agent prompt 自动感知可用能力
- **部署变化**: 新增 4 个 MCP Server 进程（检索/记忆/用户/审计）