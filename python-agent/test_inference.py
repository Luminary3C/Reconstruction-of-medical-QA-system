"""直接推理测试脚本 —— 测试 LLM 直调、AgentService、FastAPI 端点。"""
import asyncio
import sys
sys.path.insert(0, ".")

from app.services.llm_service import LLMService

SYSTEM_PROMPT = """You are a helpful, knowledgeable AI assistant.
Answer the user's question clearly, accurately, and concisely.
If you don't know something, say so honestly."""


async def test_direct_llm(question: str):
    """测试1: 直接 LLM 流式推理"""
    print(f"\n{'='*60}")
    print(f"[直接LLM] Q: {question}")
    print(f"{'='*60}")
    print("A: ", end="", flush=True)

    llm = LLMService()
    async for token in llm.stream_chat(SYSTEM_PROMPT, question):
        print(token, end="", flush=True)
    print("\n")


async def test_agent_service(question: str):
    """测试2: AgentService (含 connect + MCP 客户端 + retrieval)"""
    from app.services.agent_service import AgentService

    print(f"\n{'='*60}")
    print(f"[AgentService] Q: {question}")
    print(f"{'='*60}")

    agent = AgentService()
    await agent.connect()
    try:
        print("A: ", end="", flush=True)
        async for token in agent.process(
            user_message=question,
            user_id="test-user",
            session_id="test-session",
            short_term_context=[],
        ):
            print(token, end="", flush=True)
        print("\n")
    finally:
        await agent.close()


async def test_fastapi_endpoint():
    """测试3: FastAPI /v1/chat/completions 端点（流式 + 非流式）"""
    from fastapi.testclient import TestClient
    from app.main import app

    print(f"\n{'='*60}")
    print("[FastAPI] 测试 /health 端点")
    print(f"{'='*60}")

    with TestClient(app, raise_server_exceptions=False) as client:
        # health check
        resp = client.get("/health")
        print(f"  health: {resp.status_code} -> {resp.json()}")

        # non-streaming
        print(f"\n{'='*60}")
        print("[FastAPI 非流式] Q: Hello, introduce yourself in Chinese")
        print(f"{'='*60}")
        payload = {
            "messages": [{"role": "user", "content": "Hello, introduce yourself in Chinese"}],
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  status: {resp.status_code}")
            print(f"  A: {data['choices'][0]['message']['content'][:300]}...")
        else:
            print(f"  ERROR: {resp.status_code} -> {resp.text[:300]}")

        # streaming
        print(f"\n{'='*60}")
        print("[FastAPI 流式] Q: 请用中文解释什么是RAG?")
        print(f"{'='*60}")
        payload["stream"] = True
        payload["messages"][0]["content"] = "请用中文解释什么是RAG?"
        with client.stream("POST", "/v1/chat/completions", json=payload) as resp:
            print(f"  status: {resp.status_code}")
            print("  A: ", end="", flush=True)
            chunk_count = 0
            for line in resp.iter_lines():
                if line and line.startswith("data: ") and "[DONE]" not in line:
                    try:
                        import json
                        chunk = json.loads(line[6:])
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            print(token, end="", flush=True)
                            chunk_count += 1
                    except Exception:
                        pass
            print(f"\n  (received {chunk_count} tokens)")
            assert chunk_count > 0, "No content tokens received in streaming mode"


async def main():
    try:
        await test_direct_llm("你好，请用中文做一下自我介绍?")
    except Exception as e:
        print(f"  [直接LLM 失败] {e}")

    try:
        await test_agent_service("请介绍一下你自己，并列举你能使用的工具?")
    except Exception as e:
        print(f"  [AgentService 失败] {e}")

    try:
        await test_fastapi_endpoint()
    except Exception as e:
        print(f"  [FastAPI 失败] {type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print("所有测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
