"""Aggregates every v1 endpoint router into one ``APIRouter``.

``main.py`` mounts this single router under the ``/v1`` prefix. Individual
endpoint modules (``endpoints/health.py`` today; ``endpoints/requests.py``
etc. from Phase 13 onward) never know their own URL prefix — that's decided
here, in one place, which is what makes introducing a ``/v2`` later a
non-breaking, additive change rather than a rename sweep across the
codebase.
"""

from fastapi import APIRouter

from app.grocery.api.v1.endpoints import health, requests

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(requests.router)
