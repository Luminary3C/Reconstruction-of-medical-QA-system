import asyncio
import time
import uuid
from app.services.gatekeeper_service import GateKeeperService, REJECT_RESPONSE, CLARIFY_RESPONSE
from app.services.context_builder import ContextBuilder
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.db.vector_store import VectorStore
from app.services.reranker_service import RerankerService
from app.services.verification_service import VerificationService
from app.services.trace_context import TraceContext, GateTrace, RetrievalTrace, GenerationTrace, VerificationTrace
from app.mcp.clients.memory_client import MemoryMCPClient
from app.mcp.clients.audit_client import AuditMCPClient
from app.mcp.clients.user_client import UserMCPClient


class AgentService:
    """Medical Agent — layered decision + selective retrieval + streaming generation."""

    def __init__(self):
        self.gatekeeper = GateKeeperService()
        self.context_builder = ContextBuilder()
        self.llm = LLMService()
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore()
        self.reranker = RerankerService()
        self.verification = VerificationService()
        self._connected = False

        self.memory = MemoryMCPClient()
        self.audit = AuditMCPClient()
        self.user = UserMCPClient()

    async def connect(self):
        if self._connected:
            return
        for client in (self.memory, self.audit, self.user):
            try:
                await client.connect()
            except Exception:
                pass
        self._connected = True

    async def close(self):
        self._connected = False
        for client in (self.memory, self.audit, self.user):
            try:
                await client.close()
            except Exception:
                pass

    async def process_with_gate(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        short_term_context: list[str],
        gate,
        trace: TraceContext | None = None,
    ):
        """Process with a pre-computed gate result — skip gatekeeper step."""

        if trace is None:
            trace = TraceContext(
                request_id=uuid.uuid4().hex[:16],
                user_id=user_id,
                session_id=session_id,
                query=user_message,
            )
            trace.start()

        # Gate trace (already computed)
        trace.gate = GateTrace(
            intent=gate.intent,
            reason=gate.reason,
            safety_tags=gate.safety_tags,
            rewritten_query=gate.rewritten_query,
        )

        # Use rewritten query for retrieval (improves recall for referential queries)
        retrieval_query = gate.rewritten_query or user_message

        # ── Selective retrieval based on gate decision ──
        rag_docs: list[dict] = []
        long_term_memories: list[dict] = []
        retrieval_tasks = []
        retrieval_labels = []

        t0 = time.time()

        if gate.needs_rag:
            retrieval_tasks.append(self.vector_store.search(retrieval_query))
            retrieval_labels.append("rag")
        if gate.needs_memory:
            retrieval_tasks.append(self.memory.search_long_term_memory(retrieval_query, user_id))
            retrieval_labels.append("memory")

        if retrieval_tasks:
            try:
                results = await asyncio.gather(*retrieval_tasks)
                for label, result in zip(retrieval_labels, results):
                    if label == "rag":
                        rag_docs = result
                    elif label == "memory":
                        long_term_memories = result
            except Exception:
                pass

        # ── Rerank: refine coarse retrieval results ──
        reranked_top = 0
        if rag_docs:
            try:
                rag_docs = await self.reranker.rerank(retrieval_query, rag_docs)
                reranked_top = len(rag_docs)
            except Exception:
                pass
        if long_term_memories:
            try:
                long_term_memories = await self.reranker.rerank(
                    retrieval_query, long_term_memories, content_key="content",
                )
            except Exception:
                pass

        trace.retrieval = RetrievalTrace(
            rag_doc_count=len(rag_docs),
            memory_doc_count=len(long_term_memories),
            reranked_top_n=reranked_top,
            latency_ms=round((time.time() - t0) * 1000, 1),
        )

        # ── Generate with medical context ──
        system_prompt = self.context_builder.build(
            user_query=user_message,
            short_term_context=short_term_context,
            rag_docs=rag_docs,
            long_term_memories=long_term_memories,
        )

        t1 = time.time()
        full_answer = ""
        async for token in self.llm.stream_chat(system_prompt, user_message):
            full_answer += token
            yield token

        trace.generation = GenerationTrace(
            model=self.llm._model if hasattr(self.llm, "_model") else "",
            token_count=len(full_answer),
            latency_ms=round((time.time() - t1) * 1000, 1),
        )

        # ── Sync verification after stream ends — emit disclaimer event ──
        verification_result = None
        t2 = time.time()
        try:
            verification_result = await self.verification.verify(full_answer, user_message, rag_docs)
        except Exception:
            pass

        trace.verification = VerificationTrace(
            passed=verification_result.passed if verification_result else True,
            confidence=verification_result.confidence if verification_result else "unknown",
            safety_violations=verification_result.safety_violations if verification_result else [],
            latency_ms=round((time.time() - t2) * 1000, 1),
        )

        # Build disclaimer suffix from verification result
        disclaimer = self._build_disclaimer(verification_result)
        if disclaimer:
            yield {"type": "verification", "disclaimer": disclaimer, "confidence": trace.verification.confidence}

        trace.mark_total()

        # ── Async post-process (embedding + audit + trace) ──
        asyncio.create_task(self._post_process(
            gate, user_id, session_id, user_message, full_answer, rag_docs, trace,
        ))

    async def process(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        short_term_context: list[str],
    ):
        trace = TraceContext(
            request_id=uuid.uuid4().hex[:16],
            user_id=user_id,
            session_id=session_id,
            query=user_message,
        )
        trace.start()

        # ── Step 1: GateKeeper — safety + intent + query rewrite ──
        gate = await self.gatekeeper.check(user_message, short_term_context)

        # Reject: return fixed safety notice
        if gate.intent == "reject":
            trace.gate = GateTrace(
                intent="reject", reason=gate.reason, safety_tags=gate.safety_tags,
            )
            trace.mark_total()
            asyncio.create_task(self._audit_reject(user_id, user_message, gate, trace))
            yield REJECT_RESPONSE
            return

        # Clarify: return clarification prompt
        if gate.intent == "clarify":
            trace.gate = GateTrace(
                intent="clarify", reason=gate.reason,
            )
            trace.mark_total()
            asyncio.create_task(self._audit_clarify(user_id, user_message, gate, trace))
            yield CLARIFY_RESPONSE
            return

        # ── Step 2-4: same as process_with_gate ──
        async for token in self.process_with_gate(
            user_message, user_id, session_id, short_term_context, gate, trace,
        ):
            yield token

    async def _post_process(
        self, gate, user_id: str, session_id: str, question: str, answer: str,
        rag_docs: list[dict], trace: TraceContext,
    ):
        """Embedding write-back + audit logging + trace emission — fire-and-forget."""
        # Embedding write-back
        try:
            combined = f"Q: {question} A: {answer}"
            emb = await self.embedding.embed(combined)
            await self.memory.save_conversation(
                user_id=user_id,
                question=question,
                answer=answer,
                metadata={"session_id": session_id, "embedding": emb},
            )
        except Exception:
            pass

        # Audit log
        try:
            detail = {
                "intent": gate.intent,
                "session_id": session_id,
                "rewritten_query": gate.rewritten_query,
                "verification": {
                    "passed": trace.verification.passed,
                    "confidence": trace.verification.confidence,
                    "safety_violations": trace.verification.safety_violations,
                },
            }
            await self.audit.audit_log(
                event_type="chat_complete",
                user_id=user_id,
                detail=detail,
            )
        except Exception:
            pass

        # Emit full trace
        try:
            await self.audit.audit_log(
                event_type="agent_trace",
                user_id=user_id,
                detail=trace.model_dump(),
            )
        except Exception:
            pass

    @staticmethod
    def _build_disclaimer(verification_result) -> str:
        """Build disclaimer suffix as markdown blockquote for distinct rendering."""
        if not verification_result:
            return ""
        parts = []
        if not verification_result.passed:
            parts.append("\u26a0\ufe0f \u6b64\u56de\u7b54\u5b58\u5728\u6f5c\u5728\u5b89\u5168\u98ce\u9669\uff0c\u8bf7\u52a1\u5fc5\u54a8\u8be2\u4e13\u4e1a\u533b\u751f\u3002")
        if verification_result.confidence == "low":
            parts.append("\U0001f4cc \u4ee5\u4e0a\u4fe1\u606f\u77e5\u8bc6\u5e93\u8986\u76d6\u4e0d\u8db3\uff0c\u4ec5\u4f9b\u53c2\u8003\uff0c\u5efa\u8bae\u54a8\u8be2\u4e13\u4e1a\u533b\u751f\u83b7\u53d6\u51c6\u786e\u5efa\u8bae\u3002")
        elif verification_result.confidence == "medium":
            parts.append("\U0001f4cb \u4ee5\u4e0a\u4fe1\u606f\u90e8\u5206\u6765\u6e90\u8986\u76d6\u4e0d\u5b8c\u6574\uff0c\u4ec5\u4f9b\u53c2\u8003\u3002")
        if not parts:
            return ""
        # Wrap as markdown blockquote so frontend renders it distinctly
        lines = "> " + "\n> ".join(parts)
        return f"\n\n---\n{lines}"

    async def _audit_reject(self, user_id: str, message: str, gate, trace: TraceContext):
        try:
            await self.audit.audit_log(
                event_type="gate_reject",
                user_id=user_id,
                detail={"safety_tags": gate.safety_tags, "reason": gate.reason, "message_snippet": message[:100]},
            )
            await self.audit.audit_log(
                event_type="agent_trace",
                user_id=user_id,
                detail=trace.model_dump(),
            )
        except Exception:
            pass

    async def _audit_clarify(self, user_id: str, message: str, gate, trace: TraceContext):
        try:
            await self.audit.audit_log(
                event_type="gate_clarify",
                user_id=user_id,
                detail={"reason": gate.reason, "message_snippet": message[:100]},
            )
            await self.audit.audit_log(
                event_type="agent_trace",
                user_id=user_id,
                detail=trace.model_dump(),
            )
        except Exception:
            pass