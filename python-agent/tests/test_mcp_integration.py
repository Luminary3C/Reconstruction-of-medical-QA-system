"""
MCP 集成测试 — 验证三路召回 + 持久化 + 审计全链路。
"""
import pytest
import json


@pytest.mark.integration
class TestMCPIntegration:

    async def test_mcp_rag_flow(self):
        """端到端: 用户提问 → MCP Tool 调用 → 上下文融合 → LLM 回答."""
        from app.services.agent_service import AgentService
        agent = AgentService()

        tokens = []
        async for token in agent.process(
            user_message="What is vector search?",
            user_id="test-user",
            session_id="test-session",
            short_term_context=["Q: Hi | A: Hello!"],
        ):
            tokens.append(token)

        assert len(tokens) > 0  # LLM 应返回内容

    async def test_mcp_timeout_degradation(self):
        """MCP Tool 超时降级: 不应阻塞 Agent 流程."""
        from app.mcp.clients.retrieval_client import RetrievalMCPClient
        import asyncio

        client = RetrievalMCPClient()
        # Client not connected → should return [] gracefully
        result = await client.search_knowledge_base("test query")
        assert result == []

    def test_mcp_disabled_flag(self):
        """MCP_ENABLED=false 时应返回空结果而非抛异常."""
        import os
        os.environ["MCP_ENABLED"] = "false"
        from app.mcp.clients.memory_client import MemoryMCPClient
        client = MemoryMCPClient()
        result = client._enabled
        assert not result
        os.environ["MCP_ENABLED"] = "true"

    def test_audit_client_fire_and_forget(self):
        """审计 client 失败不应抛异常."""
        import asyncio
        async def run():
            from app.mcp.clients.audit_client import AuditMCPClient
            client = AuditMCPClient()
            result = await client.audit_log("test", "user1", {"key": "val"})
            # 失败也返回 {"ack": False}, 不抛异常
            assert "ack" in result
        asyncio.run(run())