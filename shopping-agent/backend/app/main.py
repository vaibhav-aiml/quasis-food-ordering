"""Application entrypoint.

Uses an application-factory pattern (``create_app()``) rather than a bare
module-level ``app = FastAPI()``. This is what lets tests build a fresh,
isolated app instance — optionally with overridden settings — instead of
importing (and mutating) one shared singleton. The module-level ``app`` at
the bottom of this file exists purely for ``uvicorn app.main:app`` to find.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a ``FastAPI`` application instance.

    Args:
        settings: Optional explicit ``Settings`` to use instead of the
            cached process-wide instance. Tests pass this to run against
            controlled configuration without touching environment
            variables or the ``lru_cache`` singleton.
    """

    resolved_settings = settings or get_settings()
    setup_logging(resolved_settings)
    logger = get_logger("app.startup")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_startup",
            extra={
                "app_env": resolved_settings.app_env,
                "app_version": resolved_settings.app_version,
            },
        )
        yield
        logger.info("application_shutdown")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )

    # If explicit settings were provided (e.g. by a test), make sure every
    # `Depends(get_settings)` in the app resolves to that same instance
    # rather than the cached process-wide one.
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: resolved_settings

    app.include_router(api_router, prefix="/v1")

    return app


# What `uvicorn app.main:app --reload` imports and serves.
app = create_app()
