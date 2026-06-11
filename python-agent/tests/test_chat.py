import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_non_streaming():
    """端到端测试: chat completions 非流式路径（不依赖外部服务时返回空上下文)."""
    payload = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "user_id": "test-user",
        "session_id": "test-session",
        "short_term_context": ["Q: Hi | A: Hello!"],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0


def test_chat_streaming():
    """端到端测试: chat completions 流式路径."""
    payload = {
        "messages": [{"role": "user", "content": "Tell me a short joke"}],
        "stream": True,
        "user_id": "test-user",
        "session_id": "test-session",
        "short_term_context": [],
    }
    response = client.post("/v1/chat/completions", json=payload, stream=True)
    assert response.status_code == 200

    chunks = []
    for line in response.iter_lines():
        if line:
            chunks.append(line)

    assert len(chunks) > 0
    # last non-empty line should be [DONE]
    assert any("DONE" in c for c in chunks)


def test_empty_messages():
    """边界: 空消息列表应正确回退."""
    payload = {
        "messages": [],
        "stream": False,
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
