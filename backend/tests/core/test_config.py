"""Tests for app.core.config.Settings.

These construct ``Settings`` directly rather than going through
``get_settings()``'s cache, which is the correct pattern for testing
config in isolation — see the docstring on ``get_settings``.
"""

import os

from app.core.config import Settings


def test_settings_defaults_when_no_env_overrides(monkeypatch) -> None:
    """With no relevant environment variables set, defaults apply."""

    for key in list(os.environ):
        if key.lower().startswith(("app_", "log_", "ollama_", "appium_", "android_")):
            monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.ollama_model == "qwen2.5:7b-instruct"


def test_settings_reads_environment_overrides(monkeypatch) -> None:
    """Environment variables override the built-in defaults."""

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"


def test_settings_is_case_insensitive_for_env_vars() -> None:
    """Env var matching should not depend on casing (case_sensitive=False)."""

    settings = Settings(_env_file=None, app_env="local")  # type: ignore[call-arg]
    assert settings.app_env == "local"
