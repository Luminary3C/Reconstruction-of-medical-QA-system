import httpx
from openai import AsyncOpenAI
from app.core.config import settings


class LLMService:

    def __init__(self):
        self._client = None
        self._model = settings.llm_model
        self._base_url = settings.llm_base_url
        self._api_key = settings.llm_api_key

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key or "sk-placeholder",
                timeout=httpx.Timeout(180.0, connect=15.0, read=300.0, write=60.0),
            )
        return self._client

    async def stream_chat(self, system_prompt: str, user_message: str):
        stream = await self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content