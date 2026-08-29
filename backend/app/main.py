"""Application entrypoint for Quasis Quick-Commerce Backend.

Uses an application-factory pattern (``create_app()``) rather than a bare
module-level ``app = FastAPI()``, enabling isolated test setups while serving
the singleton ``app`` for ``uvicorn app.main:app``.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging
from app.grocery.api.v1.router import api_v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a ``FastAPI`` application instance."""
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
        title="Quasis Quick-Commerce Backend",
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: resolved_settings

    # Mount grocery router under /v1 and /api/v1
    app.include_router(api_v1_router, prefix="/v1")
    app.include_router(api_v1_router, prefix="/api/v1")

    if resolved_settings.app_env != "test":
        @app.get("/health")
        async def health_check():
            return {"status": "ok"}

    return app


# Module-level application instance for uvicorn
app = create_app()
