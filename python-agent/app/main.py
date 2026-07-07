import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.api.v1.chat import router as chat_router
from app.api.v1.knowledge import router as knowledge_router
from app.core.config import settings
from app.services.agent_service import AgentService

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = AgentService()
    await agent.connect()
    app.state.agent_service = agent
    yield
    await agent.close()


app = FastAPI(title="RAG Python Agent", version="0.1.0", lifespan=lifespan)

app.include_router(chat_router, prefix="/v1")
app.include_router(knowledge_router, prefix="/v1")


def get_agent(request: Request) -> AgentService:
    return request.app.state.agent_service


@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.server_host, port=settings.server_port, reload=True)
