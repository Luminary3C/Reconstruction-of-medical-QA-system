from pathlib import Path
from jinja2 import Template

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load(name: str) -> Template:
    path = PROMPTS_DIR / name
    if not path.exists():
        return Template("")
    return Template(path.read_text(encoding="utf-8"))


class ContextBuilder:

    def __init__(self):
        self.simple_qa = _load("simple_qa.j2")
        self.history_chat = _load("history_chat.j2")
        self.clarify = _load("clarify.j2")

    def build(
        self,
        intent: str,
        user_query: str,
        short_term_context: list[str],
        rag_docs: list[dict],
        long_term_memories: list[dict],
    ) -> str:
        if intent == "history":
            return self.history_chat.render(
                short_term_context=short_term_context or [],
                rag_docs=rag_docs or [],
                long_term_memories=long_term_memories or [],
            )
        # simple / default
        return self.simple_qa.render(
            rag_docs=rag_docs or [],
        )

    def build_clarify(self, query: str) -> str:
        return self.clarify.render(query=query)
