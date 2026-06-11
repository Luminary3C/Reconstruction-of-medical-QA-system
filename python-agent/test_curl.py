"""终端请求测试 —— 向推理服务发请求并显示 JSON 结果"""
import asyncio
import json
import sys
import httpx

# Fix Windows GBK encoding for emoji output
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8003"


async def health_check():
    print("=" * 60)
    print("1. Health Check")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/health")
        print(f"GET /health -> {r.status_code} {r.json()}")
    print()


async def test_non_streaming(query: str):
    print("=" * 60)
    print(f"2. Non-Streaming")
    print(f"   Query: {query}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(
            f"{BASE}/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": query}],
                "stream": False,
            },
        )
        print(f"   HTTP {r.status_code}")
        data = r.json()

        print("\n--- Full JSON Response ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print()
    print()


async def test_streaming(query: str):
    print("=" * 60)
    print(f"3. Streaming")
    print(f"   Query: {query}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=180) as c:
        token_count = 0
        full = ""
        sample_chunks = []
        async with c.stream(
            "POST",
            f"{BASE}/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": query}],
                "stream": True,
            },
        ) as r:
            print(f"   HTTP {r.status_code}")

            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                if "[DONE]" in line:
                    print("\n   [DONE]")
                    break
                token_count += 1
                chunk = json.loads(line[6:])
                token_text = chunk["choices"][0]["delta"].get("content", "")
                full += token_text

                if len(sample_chunks) < 3:
                    sample_chunks.append(chunk)

            print(f"\n--- Sample chunks (first 3) ---")
            for i, ch in enumerate(sample_chunks):
                print(f"   chunk[{i}]: {json.dumps(ch, ensure_ascii=False)}")

            print(f"\n--- Full assembled answer ---")
            print(full)
            print(f"\n   (total chunks: {token_count})")
    print()


async def main():
    await health_check()
    await test_non_streaming("你好，用一句中文做一下自我介绍。")
    await test_streaming("What is RAG? Answer in one sentence.")


if __name__ == "__main__":
    asyncio.run(main())
