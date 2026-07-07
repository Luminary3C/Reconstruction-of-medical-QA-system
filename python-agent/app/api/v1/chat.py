import time
import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest, req: Request):
    """OpenAI-compatible chat completitions endpoint with streaming support."""
    agent_service = req.app.state.agent_service

    user_message = request.messages[-1].content if request.messages else ""
    user_id = request.user_id or "anonymous"
    session_id = request.session_id or str(uuid.uuid4())
    short_term_ctx = request.short_term_context

    # ── All intents (simple/history/clarify/reject) handled by AgentService.process() ──
    if request.stream:

        async def stream_response():
            chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())

            async for item in agent_service.process(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id,
                short_term_context=short_term_ctx,
            ):
                # Special SSE events (verification, sources)
                if isinstance(item, dict) and item.get("type") in ("verification", "sources"):
                    yield f"data: {json.dumps(item)}\n\n"
                    continue

                # Normal token
                chunk_data = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": "gpt-4o",
                    "choices": [{
                        "index": 0,
                        "delta": {"content": item},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"

            final = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": "gpt-4o",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }],
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-Id": session_id,
            },
        )

    # Non-streaming fallback
    full_response = ""
    disclaimer = ""
    async for item in agent_service.process(
        user_message=user_message,
        user_id=user_id,
        session_id=session_id,
        short_term_context=short_term_ctx,
    ):
        if isinstance(item, dict) and item.get("type") == "verification":
            disclaimer = item.get("disclaimer", "")
        else:
            full_response += item

    content = full_response
    if disclaimer:
        content += "\n" + disclaimer

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "gpt-4o",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
    }