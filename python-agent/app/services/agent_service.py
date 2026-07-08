import asyncio
import logging
import re
import time
import uuid
from app.services.gatekeeper_service import GateKeeperService
from app.services.context_builder import ContextBuilder
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.db.vector_store import VectorStore
from app.services.reranker_service import RerankerService
from app.services.verification_service import VerificationService
from app.services.keyword_engine import KeywordEngine
from app.services.trace_context import TraceContext, GateTrace, RetrievalTrace, GenerationTrace, VerificationTrace
from app.mcp.clients.memory_client import MemoryMCPClient
from app.mcp.clients.audit_client import AuditMCPClient
from app.mcp.clients.user_client import UserMCPClient

logger = logging.getLogger(__name__)

# ── Reject templates keyed by rejection_type ──

REJECT_TEMPLATES = {
    "drug_dosage": (
        "药物用量需要根据年龄、体重、肝肾功能等个体情况综合确定，AI 无法提供具体剂量建议。\n\n"
        "建议您：\n"
        "- 咨询医生或药师获取个体化用药指导\n"
        "- 用药前仔细阅读药品说明书，了解禁忌和注意事项\n\n"
        "> \u26a0\ufe0f 此信息仅供参考，用药请遵医嘱。"
    ),
    "diagnosis": (
        "AI 无法做出医学诊断，您描述的症状可能对应多种不同情况，需要医生结合检查综合判断。\n\n"
        "建议您：\n"
        "- 前往医院相关科室就诊，由医生面诊检查\n"
        "- 就诊前可记录症状变化（时间、诱因、伴随症状），帮助医生更快判断\n\n"
        "> \u26a0\ufe0f 此信息仅供参考，身体不适请及时就医。"
    ),
    "emergency": (
        "\U0001f6a8 **您描述的症状可能属于急症，请立即拨打 120 或前往最近医院的急诊科！**\n\n"
        "在等待救援或前往医院途中：\n"
        "- 保持镇静，避免剧烈活动\n"
        "- 如已知有相关病史，请告知急救人员\n"
        "- 请不要自行服药\n\n"
        "此消息为自动安全提醒，请务必立即就医。"
    ),
    "prescription": (
        "处方药需由执业医师根据个体病情评估后开具，AI 不能也不应替代医生进行处方决策。\n\n"
        "建议您：\n"
        "- 前往对应科室就诊，由医生评估病情后决定是否需要用药\n"
        "- 不要自行购买或使用他人处方药，以免延误或加重病情\n\n"
        "> \u26a0\ufe0f 此信息仅供参考，用药安全第一。"
    ),
    "treatment_plan": (
        "治疗方案需要医生结合检查结果、完整病史、个体差异综合制定，AI 无法给出完整可靠的治疗计划。\n\n"
        "建议您：\n"
        "- 前往医院相关专科就诊，与医生充分沟通病情\n"
        "- 如已确诊，可咨询主治医生获取个体化治疗建议\n\n"
        "> \u26a0\ufe0f 此信息仅供参考，切勿自行制定或调整治疗计划。"
    ),
    "default": (
        "抱歉，出于安全考虑，我无法回答此问题。\n\n"
        "建议您咨询专业医生或医疗机构获取可靠建议。"
    ),
}

# ── Clarify templates: keyword → follow-up ──

_CLARIFY_PATTERNS = [
    (r"(头疼|头痛|偏头痛)", (
        "头痛可能由多种原因引起——紧张性头痛、偏头痛、颈椎问题、血压波动等都可能导致。"
        "为了给你更准确的参考，请补充以下信息：\n\n"
        "- 疼痛的具体位置？（前额、太阳穴、后脑，还是整个头部？）\n"
        "- 疼痛性质是怎样的？（搏动性跳痛、持续性钝痛，还是针刺样？）\n"
        "- 持续多长时间了？发作频率如何？\n"
        "- 是否伴随恶心、呕吐、怕光、视力模糊等症状？"
    )),
    (r"(肚子疼|腹痛|胃痛|肚子痛)", (
        "腹痛的原因很多——从消化不良到阑尾炎都有可能。请补充：\n\n"
        "- 疼痛的具体位置？（上腹、下腹、左侧、右侧？）\n"
        "- 疼痛性质？（绞痛、隐痛、饱胀感？）\n"
        "- 持续多久了？与饮食有无关系？\n"
        "- 有无恶心、呕吐、腹泻、发热等伴随症状？"
    )),
    (r"(胸痛|胸闷|胸口)", (
        "胸闷/胸痛需要特别重视，可能与心脏、肺部、消化道或肌肉骨骼相关。请补充：\n\n"
        "- 具体位置和范围？\n"
        "- 疼痛/压迫感持续多久？是否向其他部位放射？\n"
        "- 与活动、呼吸、进食有无关系？\n"
        "- 有无心慌、出汗、呼吸困难等伴随症状？\n\n"
        "> \u26a0\ufe0f 如胸痛剧烈或伴呼吸困难，请立即就医。"
    )),
    (r"(皮肤痒|痒|疹|红点|脱皮|起皮)", (
        "皮肤问题可能涉及过敏、干燥、湿疹、真菌感染等多种情况。请补充：\n\n"
        "- 具体哪个部位？面积有多大？\n"
        "- 皮肤表面有没有红点、疹子、水疱或脱屑？\n"
        "- 什么时候开始的？有没有接触什么新物品（化妆品、食物、药品、衣物等）？\n"
        "- 有没有过敏史或类似发作史？"
    )),
    (r"(失眠|睡不好|睡不着|入睡困难|早醒)", (
        "失眠可能由压力、情绪、生活习惯、身体疾病等多种因素导致。请补充：\n\n"
        "- 持续多长时间了？\n"
        "- 是入睡困难、容易醒，还是早醒？\n"
        "- 每晚大约能睡几小时？对白天生活影响如何？\n"
        "- 近期有无工作压力、生活变故或情绪低落？"
    )),
]


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
        self.keyword_engine = KeywordEngine()
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
        try:
            await self.keyword_engine.reload()
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

    # ────────────────────────────────
    # Main entry: optimistic pipeline
    # ────────────────────────────────

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

        # ── Fire GateKeeper and retrieval in parallel ──
        gate_task = asyncio.create_task(
            self.gatekeeper.check(user_message, short_term_context),
        )
        retrieval_task = asyncio.create_task(
            self._optimistic_retrieval(user_message),
        )

        gate = await gate_task

        # ── Reject: template, discard retrieval ──
        if gate.intent == "reject":
            retrieval_task.cancel()
            trace.gate = GateTrace(
                intent="reject",
                reason=gate.reason,
                safety_tags=gate.safety_tags,
            )
            trace.mark_total()
            asyncio.create_task(self._audit_reject(user_id, user_message, gate, trace))
            template = REJECT_TEMPLATES.get(gate.rejection_type, REJECT_TEMPLATES["default"])
            yield template.format(query=user_message)
            return

        # ── Clarify: template, discard retrieval ──
        if gate.intent == "clarify":
            retrieval_task.cancel()
            trace.gate = GateTrace(
                intent="clarify",
                reason=gate.reason,
            )
            trace.mark_total()
            asyncio.create_task(self._audit_clarify(user_id, user_message, gate, trace))
            yield self._clarify_template(user_message)
            return

        # ── simple / history: use pre-fetched retrieval ──
        rag_docs, keyword_docs = await retrieval_task

        # ── Log GateKeeper result ──
        logger.info(f"[RAG] GateKeeper: intent={gate.intent}, rewritten_query='{gate.rewritten_query}', needs_rag={gate.needs_rag}, needs_memory={gate.needs_memory}")

        async for token in self.process_with_gate(
            user_message=user_message,
            user_id=user_id,
            session_id=session_id,
            short_term_context=short_term_context,
            gate=gate,
            trace=trace,
            rag_docs=rag_docs,
            keyword_docs=keyword_docs,
        ):
            yield token

    # ────────────────────────────
    # Optimistic retrieval helper
    # ────────────────────────────

    async def _optimistic_retrieval(self, query: str) -> tuple[list[dict], list[dict]]:
        """Fire semantic + keyword search in parallel, independent of GateKeeper."""
        try:
            semantic, keyword = await asyncio.gather(
                self.vector_store.search(query),
                asyncio.to_thread(self.keyword_engine.search, query),
            )
            return semantic, keyword
        except Exception:
            return [], []

    # ──────────────────────────────────
    # process_with_gate (with pre-fetched retrieval)
    # ──────────────────────────────────

    async def process_with_gate(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        short_term_context: list[str],
        gate,
        trace: TraceContext,
        rag_docs: list[dict] | None = None,
        keyword_docs: list[dict] | None = None,
    ):
        """Process with a pre-computed gate result and optional pre-fetched docs."""

        retrieval_query = gate.rewritten_query or user_message

        t0 = time.time()

        # ── Use pre-fetched results, or fetch if not provided ──
        if rag_docs is None and keyword_docs is None:
            retrieval_tasks = []
            retrieval_labels = []

            if gate.needs_rag:
                retrieval_tasks.append(self.vector_store.search(retrieval_query))
                retrieval_labels.append("rag")
                retrieval_tasks.append(asyncio.to_thread(self.keyword_engine.search, retrieval_query))
                retrieval_labels.append("keyword")

            if retrieval_tasks:
                try:
                    results = await asyncio.gather(*retrieval_tasks)
                    for label, result in zip(retrieval_labels, results):
                        if label == "rag":
                            rag_docs = result
                        elif label == "keyword":
                            keyword_docs = result
                except Exception:
                    pass

        long_term_memories: list[dict] = []
        if gate.needs_memory:
            try:
                long_term_memories = await self.memory.search_long_term_memory(retrieval_query, user_id)
                logger.info(f"[RAG] Memory: retrieved {len(long_term_memories)} long-term memories")
            except Exception:
                pass

        # ── Log retrieval results ──
        logger.info(f"[RAG] Semantic: {len(rag_docs or [])} docs, Keyword: {len(keyword_docs or [])} docs")

        # ── RRF merge semantic + keyword ──
        if keyword_docs:
            rag_docs = self._merge_dedup(rag_docs or [], keyword_docs, settings_rrf_top_k=20)
            logger.info(f"[RAG] After RRF merge: {len(rag_docs)} unique docs")

        # ── Rerank ──
        reranked_top = 0
        sources: list[dict] = []
        if rag_docs:
            try:
                rag_docs = await self.reranker.rerank(retrieval_query, rag_docs)
                reranked_top = len(rag_docs)
                # Extract top sources for citation
                sources = [
                    {"title": doc.get("title", "Unknown"), "score": round(doc.get("rrf_score", 0), 3)}
                    for doc in rag_docs[:5]
                ]
                top_summaries = [f"{d.get('title', 'Unknown')}({d.get('rrf_score', 0):.3f})" for d in rag_docs[:3]]
                logger.info(f"[RAG] Reranked top docs: {top_summaries}")
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

        trace.gate = GateTrace(
            intent=gate.intent,
            reason=gate.reason,
            safety_tags=gate.safety_tags,
            rewritten_query=gate.rewritten_query,
        )

        # ── Generate with intent-specific prompt ──
        system_prompt = self.context_builder.build(
            intent=gate.intent,
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
            model=getattr(self.llm, "_model", ""),
            token_count=len(full_answer),
            latency_ms=round((time.time() - t1) * 1000, 1),
        )

        # ── Async verification (fire-and-forget, no stream blocking) ──
        asyncio.create_task(self._verify_and_notify(
            full_answer, user_message, rag_docs, gate, sources, trace,
        ))

        # ── Send sources event if RAG was used ──
        if gate.intent in ("simple", "history") and sources:
            logger.info(f"[RAG] Sending {len(sources)} sources: {[s['title'] for s in sources]}")
            yield {"type": "sources", "sources": sources}

        trace.mark_total()

        # ── Send sources event if RAG was used ──
        if gate.intent in ("simple", "history") and sources:
            logger.info(f"[RAG] Sending {len(sources)} sources: {[s['title'] for s in sources]}")
            yield {"type": "sources", "sources": sources}

        trace.mark_total()

        asyncio.create_task(self._post_process(
            gate, user_id, session_id, user_message, full_answer, rag_docs, trace,
        ))

    # ────────────────────
    # Clarify template (keyword-match, generic fallback)
    # ────────────────────

    @staticmethod
    def _clarify_template(query: str) -> str:
        for pattern, template in _CLARIFY_PATTERNS:
            if re.search(pattern, query):
                return f"你提到「{query}」。{template}\n\n补充这些信息后，我可以提供更有针对性的分析。"
        # Generic fallback
        return (
            f"你提到「{query}」，但描述较为笼统，为了给你更准确的参考，请补充以下信息：\n\n"
            "- 症状持续多长时间了？严重程度如何？\n"
            "- 有无其他伴随症状？\n"
            "- 既往有无相关病史或正在服用的药物？\n"
            "- 年龄和性别？\n\n"
            "补充更多细节后，我能更好帮你分析。"
        )

    # ────────────────────
    # Async verification + audit
    # ────────────────────

    async def _verify_and_notify(
        self, full_answer: str, user_message: str, rag_docs: list[dict],
        gate, sources: list[dict], trace: TraceContext,
    ):
        """Run verification after streaming completes, update trace and audit."""
        verification_result = None
        t2 = time.time()
        try:
            verification_result = await self.verification.verify(full_answer, user_message, rag_docs)
            logger.info(f"[RAG] Verification: passed={verification_result.passed}, confidence={verification_result.confidence}, violations={verification_result.safety_violations}")
        except Exception:
            logger.info("[RAG] Verification: failed with exception")

        trace.verification = VerificationTrace(
            passed=verification_result.passed if verification_result else True,
            confidence=verification_result.confidence if verification_result else "unknown",
            safety_violations=verification_result.safety_violations if verification_result else [],
            latency_ms=round((time.time() - t2) * 1000, 1),
        )

        disclaimer = self._build_disclaimer(verification_result)
        if disclaimer:
            logger.info(f"[RAG] Verification disclaimer generated: confidence={trace.verification.confidence}")

        await self._post_process(gate, trace.user_id, trace.session_id, user_message, full_answer, rag_docs, trace)

    # ────────────────────
    # RRF merge (unchanged)
    # ────────────────────

    def _merge_dedup(self, semantic_docs: list[dict], keyword_docs: list[dict], settings_rrf_top_k: int = 20) -> list[dict]:
        """Reciprocal Rank Fusion: merge semantic and keyword results, dedup by chunk_id."""
        if not keyword_docs:
            return semantic_docs
        if not semantic_docs:
            return keyword_docs

        RRF_K = 60
        scores: dict[int, float] = {}
        doc_map: dict[int, dict] = {}

        for rank, doc in enumerate(semantic_docs):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
            doc_map[cid] = doc

        for rank, doc in enumerate(keyword_docs):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
            if cid not in doc_map:
                doc_map[cid] = {**doc, "similarity": 0.0}

        merged = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
        result = []
        for cid in merged[:settings_rrf_top_k]:
            d = dict(doc_map[cid])
            d["rrf_score"] = round(scores[cid], 6)
            d["bm25_score"] = next(
                (k["bm25_score"] for k in keyword_docs if k["chunk_id"] == cid), 0.0
            )
            result.append(d)

        return result

    # ────────────────────
    # Post-process & audit (unchanged)
    # ────────────────────

    async def _post_process(
        self, gate, user_id: str, session_id: str, question: str, answer: str,
        rag_docs: list[dict], trace: TraceContext,
    ):
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

        try:
            await self.audit.audit_log(
                event_type="agent_trace",
                user_id=user_id,
                detail=trace.model_dump(),
            )
        except Exception:
            pass

    @staticmethod
    def _build_disclaimer(verification_result, gate, rag_docs) -> str:
        """动态生成免责声明：根据安全违规、置信度、是否有知识库检索结果来调整内容。"""
        if not verification_result:
            return ""

        parts = []

        # ── 安全违规：逐条列出具体问题 ──
        if not verification_result.passed:
            if verification_result.safety_violations:
                parts.append("\u26a0\ufe0f " + "\uff1b".join(verification_result.safety_violations[:3]))
            elif verification_result.warnings:
                parts.append("\u26a0\ufe0f " + " \uff1b".join(verification_result.warnings[:3]))
            else:
                parts.append("\u26a0\ufe0f \u6b64\u56de\u7b54\u5b58\u5728\u6f5c\u5728\u5b89\u5168\u98ce\u9669\uff0c\u8bf7\u52a1\u5fc5\u54a8\u8be2\u4e13\u4e1a\u533b\u751f\u3002")

        # ── 置信度：根据是否有 RAG 结果给出不同的说明 ──
        if verification_result.confidence == "low":
            if rag_docs:
                parts.append("\U0001f4cc \u77e5\u8bc6\u5e93\u76f8\u5173\u5185\u5bb9\u6709\u9650\uff0c\u4ee5\u4e0a\u4fe1\u606f\u4ec5\u4f9b\u53c2\u8003\u3002")
            else:
                parts.append("\U0001f4cc \u672a\u68c0\u7d22\u5230\u76f8\u5173\u77e5\u8bc6\u5e93\u6587\u732e\uff0c\u4ee5\u4e0a\u56de\u7b54\u57fa\u4e8e\u901a\u7528\u533b\u5b66\u77e5\u8bc6\uff0c\u4ec5\u4f9b\u53c2\u8003\u3002")
        elif verification_result.confidence == "medium":
            parts.append("\U0001f4cb \u90e8\u5206\u4fe1\u606f\u6765\u6e90\u8986\u76d6\u4e0d\u5b8c\u6574\uff0c\u4ec5\u4f9b\u53c2\u8003\u3002")

        # ── 一切正常（高置信度 + 无安全违规）→ 不显示声明 ──
        if not parts:
            return ""

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
