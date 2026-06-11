import json
import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.core.config import settings


class GateResult(BaseModel):
    intent: str              # simple / history / clarify / reject
    reason: str = ""
    safety_tags: list[str] = []
    needs_rag: bool = True
    needs_memory: bool = False
    rewritten_query: str = ""


REJECT_RESPONSE = (
    "抱歉，我无法提供此类建议。涉及具体用药剂量、诊断结论或治疗方案的问题，"
    "请咨询专业医生或医疗机构。AI 助手仅提供一般性医学知识参考，不构成医疗建议。"
)

CLARIFY_RESPONSE = (
    "您的问题描述较为笼统，为了给出更有参考价值的回答，请您补充以下信息：\n"
    "- 具体症状持续了多久？\n"
    "- 是否伴随其他症状？\n"
    "- 是否有既往病史或正在服用药物？\n"
    "- 年龄和性别？\n\n"
    "补充后我将为您提供更精准的医学知识参考。"
)

GATE_SYSTEM_PROMPT = """\
You are a medical question triage system. Analyze the user's question and return a JSON object with your decision.

## Decision Rules

1. SAFETY — Reject questions that request:
   - Specific drug dosage or prescription recommendations
   - Direct diagnosis conclusions (e.g., "What disease do I have?")
   - Treatment plans for specific conditions
   - If the question poses a medical safety risk → intent=reject

2. INTENT classification:
   - "simple": General medical knowledge question with no reference to past conversations
   - "history": User explicitly or implicitly references previous conversation context
     (keywords: "之前说的", "上次", "你之前提到", "we discussed", "you said before", "上次聊的", "刚才说的")
   - "clarify": Question is too vague to provide a meaningful answer
     (e.g., just "头疼" without duration/severity/context, single symptom without details)

3. RETRIEVAL needs:
   - needs_rag: true for most medical domain questions (they benefit from knowledge base)
   - needs_memory: true ONLY when intent=history (user references past conversations)

4. QUERY REWRITE:
   - Rewrite the user's question into a self-contained, search-optimized query.
   - For intent=history: resolve all references to previous conversations.
     Example: "刚才说的那个降压药" → "ACEI类降压药物名称推荐"
   - For intent=simple: make the query more precise and search-friendly.
     Example: "头疼怎么办" → "头痛 常见病因 治疗方法 就诊建议"
   - For intent=clarify/reject: set rewritten_query to the original question.

## Output Format

Return ONLY a JSON object (no other text):
{"intent": "simple|history|clarify|reject", "reason": "...", "safety_tags": [...], "needs_rag": true/false, "needs_memory": true/false, "rewritten_query": "..."}
"""


class GateKeeperService:
    """Medical safety filter + intent classification + query rewrite — single LLM call."""

    def __init__(self):
        self._client = None
        model = settings.gatekeeper_model or settings.llm_model
        self._model = model

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key or "sk-placeholder",
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._client

    async def check(self, user_message: str, short_term_context: list[str] | None = None) -> GateResult:
        if not settings.gatekeeper_enabled:
            return GateResult(intent="simple", needs_rag=True, needs_memory=False, rewritten_query=user_message)

        context_hint = ""
        if short_term_context:
            context_hint = "\n## Current session context (recent messages):\n" + "\n".join(
                f"- {msg}" for msg in short_term_context
            )

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": GATE_SYSTEM_PROMPT + context_hint},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return GateResult(
                intent=parsed.get("intent", "simple"),
                reason=parsed.get("reason", ""),
                safety_tags=parsed.get("safety_tags", []),
                needs_rag=parsed.get("needs_rag", True),
                needs_memory=parsed.get("needs_memory", False),
                rewritten_query=parsed.get("rewritten_query", user_message),
            )
        except Exception:
            return GateResult(intent="simple", needs_rag=True, needs_memory=False, rewritten_query=user_message)