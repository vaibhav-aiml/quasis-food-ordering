"""Health check endpoint.

A liveness/readiness probe: confirms the process is up and configuration
loaded successfully. Deliberately has no dependency on the LLM, Appium, or
any store adapter — those get their own readiness signals in later phases
once they exist. A health check that depends on everything downstream stops
being useful the moment any one downstream thing is slow or flaky.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Shape of the health check response."""

    status: str
    app_name: str
    app_version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return basic liveness information about the running application."""

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.app_env,
    )
