from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from beauty_creator_agent.api.health import router as health_router
from beauty_creator_agent.api.tasks import router as tasks_router
from beauty_creator_agent.core.config import get_settings
from beauty_creator_agent.core.logging import configure_logging
from beauty_creator_agent.services.tasks import TaskManager


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.checkpoint_backend == "postgres":
        connection_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        async with AsyncPostgresSaver.from_conn_string(connection_url) as checkpointer:
            await checkpointer.setup()
            application.state.task_manager = TaskManager(checkpointer=checkpointer)
            yield
    else:
        yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="Beauty Creator Agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.task_manager = TaskManager()
    application.include_router(health_router)
    application.include_router(tasks_router)
    return application


app = create_app()
