"""Agent Trace — structured observability for each request pipeline."""
import time
from pydantic import BaseModel


class GateTrace(BaseModel):
    intent: str = ""
    reason: str = ""
    safety_tags: list[str] = []
    rewritten_query: str = ""
    latency_ms: float = 0.0


class RetrievalTrace(BaseModel):
    rag_doc_count: int = 0
    memory_doc_count: int = 0
    reranked_top_n: int = 0
    latency_ms: float = 0.0


class GenerationTrace(BaseModel):
    model: str = ""
    token_count: int = 0
    latency_ms: float = 0.0


class VerificationTrace(BaseModel):
    passed: bool = True
    confidence: str = "high"
    safety_violations: list[str] = []
    latency_ms: float = 0.0


class TraceContext(BaseModel):
    """Full trace of a single request through the Agent pipeline."""
    request_id: str = ""
    user_id: str = ""
    session_id: str = ""
    query: str = ""

    gate: GateTrace = GateTrace()
    retrieval: RetrievalTrace = RetrievalTrace()
    generation: GenerationTrace = GenerationTrace()
    verification: VerificationTrace = VerificationTrace()

    total_latency_ms: float = 0.0

    def mark_total(self):
        """Set total_latency_ms from the start timestamp stored on the context."""
        if hasattr(self, "_start_ts"):
            self.total_latency_ms = round((time.time() - self._start_ts) * 1000, 1)

    def start(self):
        self._start_ts = time.time()