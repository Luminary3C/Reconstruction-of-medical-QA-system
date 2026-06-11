from pydantic import BaseModel, Field
from typing import Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    short_term_context: list[str] = Field(default_factory=list)

class ChatChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[dict]
