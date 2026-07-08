import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.api.v1.chat import router as chat_router
from app.api.v1.knowledge import router as knowledge_router
from app.core.config import settings
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


async def _run_alembic_upgrade():
    """Run Alembic migrations on startup to ensure DB schema is up-to-date."""
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.db.pgvector_client import engine

        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)

        async with engine.begin() as connection:
            def _upgrade(conn):
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
                head = script.get_current_head()
                if current != head:
                    from alembic import command
                    alembic_cfg.attributes["connection"] = connection
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Alembic migrations applied: %s → %s", current, head)
                else:
                    logger.info("Alembic schema up-to-date: %s", current)

            await connection.run_sync(_upgrade)
    except Exception as e:
        logger.warning("Alembic migration skipped (DB may not be ready): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _run_alembic_upgrade()
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
