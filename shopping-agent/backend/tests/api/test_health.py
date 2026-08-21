"""Tests for the /v1/health endpoint.

Uses ``create_app()`` with explicit test ``Settings`` — per the app
factory's docstring — rather than importing the module-level ``app``, so
these tests never depend on (or mutate) real environment variables.
"""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _test_client() -> TestClient:
    test_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        app_name="Test Shopping Agent",
        app_version="0.0.0-test",
    )
    app = create_app(settings=test_settings)
    return TestClient(app)


def test_health_endpoint_returns_200() -> None:
    client = _test_client()
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_endpoint_response_shape() -> None:
    client = _test_client()
    response = client.get("/v1/health")
    body = response.json()

    assert body == {
        "status": "ok",
        "app_name": "Test Shopping Agent",
        "app_version": "0.0.0-test",
        "environment": "test",
    }


def test_health_endpoint_is_versioned() -> None:
    """The unversioned path must not exist — /v1 prefixing is mandatory."""

    client = _test_client()
    response = client.get("/health")
    assert response.status_code == 404
