import json
import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.core.config import settings


class GateResult(BaseModel):
    intent: str              # simple / history / clarify / reject
    rejection_type: str = "" # drug_dosage / diagnosis / prescription / emergency / treatment_plan
    reason: str = ""
    safety_tags: list[str] = []
    needs_rag: bool = True
    needs_memory: bool = False
    rewritten_query: str = ""


GATE_SYSTEM_PROMPT = """\
你是医疗问诊分流系统。分析用户问题，返回 JSON。

## 分流规则

### 1. 安全判定（拒绝类）
涉及以下任一情况，intent=reject，并给出对应 rejection_type：
- "drug_dosage": 询问具体药品用量/用法（如"布洛芬一次吃几片""阿莫西林儿童用量"）
- "diagnosis": 要求直接诊断是否为特定疾病（如"是不是癌症""我这症状是新冠吗"）
- "prescription": 要求开药/处方/推荐具体药物（如"给我开个降压药""推荐个消炎药"）
- "emergency": 描述急性高危症状（如"胸口剧痛伴呼吸困难""突然意识模糊""大出血"）
- "treatment_plan": 要求制定完整治疗方案（如"我的糖尿病怎么治""高血压治疗方案"）

### 2. 意图分类
- "simple": 独立医学知识问答，问题自包含，无需历史上下文即可回答
- "history": 引用过往对话内容（关键词：之前说的、上次、刚刚、刚才、你提到过、那个药、接着聊...）
- "clarify": 问题太模糊（单症状无细节、仅说一个词），缺少回答所需关键信息

### 3. 检索决策
- needs_rag: 几乎所有医学问题都设为 true（reject 除外）
- needs_memory: 仅 intent=history 时为 true

### 4. Query Rewrite
- simple: 改写为搜索优化的精准医学查询，提取关键医学术语
- history: 解决所有指代词，补全上下文，改写为完整独立查询
- clarify/reject: 保持原问题不变

## 输出格式
只返回 JSON 对象，不要其他文字：
{"intent":"simple|history|clarify|reject","rejection_type":"","reason":"...","safety_tags":[],"needs_rag":true/false,"needs_memory":true/false,"rewritten_query":"..."}

## Few-Shot 示例

Q: 布洛芬一次吃几片？
A: {"intent":"reject","rejection_type":"drug_dosage","reason":"询问具体药品用量","safety_tags":["drug_dosage"],"needs_rag":false,"needs_memory":false,"rewritten_query":"布洛芬一次吃几片？"}

Q: 我头痛了三天，是不是脑瘤？
A: {"intent":"reject","rejection_type":"diagnosis","reason":"要求确认/排除特定疾病诊断","safety_tags":["diagnosis"],"needs_rag":false,"needs_memory":false,"rewritten_query":"我头痛了三天，是不是脑瘤？"}

Q: 胸口突然剧痛，喘不过气
A: {"intent":"reject","rejection_type":"emergency","reason":"描述急性高危症状","safety_tags":["emergency"],"needs_rag":false,"needs_memory":false,"rewritten_query":"胸口突然剧痛，喘不过气"}

Q: 头疼
A: {"intent":"clarify","rejection_type":"","reason":"单症状无位置、持续时间等细节","safety_tags":[],"needs_rag":false,"needs_memory":false,"rewritten_query":"头疼"}

Q: 高血压有什么症状和危害？
A: {"intent":"simple","rejection_type":"","reason":"独立医学知识问答","safety_tags":[],"needs_rag":true,"needs_memory":false,"rewritten_query":"高血压 常见症状 并发症 危害"}

Q: 上次说的那个降压药叫什么名字来着？
A: {"intent":"history","rejection_type":"","reason":"明确引用过往对话中的药物讨论","safety_tags":[],"needs_rag":true,"needs_memory":true,"rewritten_query":"降压药物 名称 分类 ACEI ARB 钙通道阻滞剂"}

Q: 糖尿病饮食上要注意什么？
A: {"intent":"simple","rejection_type":"","reason":"独立医学知识问答","safety_tags":[],"needs_rag":true,"needs_memory":false,"rewritten_query":"糖尿病 饮食控制 血糖管理 注意事项"}

Q: 帮我开点安眠药，最近睡不好
A: {"intent":"reject","rejection_type":"prescription","reason":"要求开具处方药物","safety_tags":["prescription"],"needs_rag":false,"needs_memory":false,"rewritten_query":"帮我开点安眠药，最近睡不好"}

Q: 皮肤痒
A: {"intent":"clarify","rejection_type":"","reason":"单症状无位置、特征等细节","safety_tags":[],"needs_rag":false,"needs_memory":false,"rewritten_query":"皮肤痒"}
"""

class GateKeeperService:
    """Medical safety filter + intent classification + query rewrite — single LLM call with few-shot."""

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
            context_hint = "\n## 当前会话上下文\n" + "\n".join(
                f"- {msg}" for msg in short_term_context[-6:]
            )

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": GATE_SYSTEM_PROMPT + context_hint},
                    {"role": "user", "content": f"Q: {user_message}\nA:"},
                ],
                temperature=0.0,
                max_tokens=350,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return GateResult(
                intent=parsed.get("intent", "simple"),
                rejection_type=parsed.get("rejection_type", ""),
                reason=parsed.get("reason", ""),
                safety_tags=parsed.get("safety_tags", []),
                needs_rag=parsed.get("needs_rag", True),
                needs_memory=parsed.get("needs_memory", False),
                rewritten_query=parsed.get("rewritten_query", user_message),
            )
        except Exception:
            return GateResult(intent="simple", needs_rag=True, needs_memory=False, rewritten_query=user_message)

