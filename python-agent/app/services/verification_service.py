import json
import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.core.config import settings


class VerificationResult(BaseModel):
    passed: bool = True
    safety_violations: list[str] = []
    confidence: str = "high"         # high / medium / low
    warnings: list[str] = []
    reason: str = ""


VERIFICATION_SYSTEM = """\
You are a medical answer verification system. Return ONLY valid JSON.
Review the AI-generated answer for safety and accuracy.
"""

VERIFICATION_USER = """\
## Knowledge Base Documents (source of truth)
{docs_text}

## User Question
{query}

## AI-Generated Answer
{answer}

## Verification Checklist

1. FACTUAL CONSISTENCY: Does the answer contradict any knowledge base documents above?
   - If the answer makes claims NOT supported by the documents → flag as violation
   - If the answer directly contradicts a document → flag as violation

2. SAFETY COMPLIANCE: Does the answer:
   - Recommend specific drug dosages or prescriptions?
   - Provide definitive diagnostic conclusions ("You have X disease")?
   - Omit necessary disclaimers for medical information?
   - Downplay emergency symptoms?

3. CONFIDENCE ASSESSMENT: Based on knowledge base coverage:
   - "high": Multiple sources agree, comprehensive coverage
   - "medium": Some sources support, but coverage is incomplete or partial contradiction
   - "low": No direct sources, or significant conflicting information

## Output Format

Return ONLY a JSON object:
{{"passed": true/false, "safety_violations": [...], "confidence": "high|medium|low", "warnings": [...], "reason": "..."}}\
"""


class VerificationService:
    """Post-generation answer verification — audit mode, does not modify output."""

    def __init__(self):
        self._client = None
        model = settings.verification_model or settings.llm_model
        self._model = model

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key or "sk-placeholder",
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
        return self._client

    async def verify(
        self,
        answer: str,
        query: str,
        rag_docs: list[dict],
    ) -> VerificationResult:
        if not settings.verification_enabled:
            return VerificationResult()

        if not rag_docs:
            return VerificationResult(confidence="low", warnings=["no_knowledge_base_documents"])

        # Build prompt
        docs_text = ""
        for doc in rag_docs[:5]:
            title = doc.get("title", "Document")
            content = doc.get("content", doc.get("chunk", ""))
            docs_text += f"### {title}\n{content}\n\n"

        user_prompt = VERIFICATION_USER.format(
            docs_text=docs_text or "(no knowledge base documents available)",
            query=query,
            answer=answer,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": VERIFICATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return VerificationResult(
                passed=parsed.get("passed", True),
                safety_violations=parsed.get("safety_violations", []),
                confidence=parsed.get("confidence", "high"),
                warnings=parsed.get("warnings", []),
                reason=parsed.get("reason", ""),
            )
        except Exception:
            return VerificationResult(confidence="unknown")