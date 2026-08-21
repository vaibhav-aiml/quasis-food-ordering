"""Application configuration.

A single, cached ``Settings`` instance is the only sanctioned way any code in
this project reads configuration. Nothing outside this module should call
``os.environ`` directly — see Phase 0 architecture doc, section 14.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application configuration.

    Values are loaded from environment variables (or a local ``.env`` file
    during development) in this precedence order, highest first:

    1. Real process environment variables
    2. ``.env`` file values
    3. The defaults declared below

    This mirrors standard 12-factor configuration practice and requires no
    rework when the project moves beyond local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    app_name: str = "Intent-to-Action Shopping Agent"
    app_version: str = "0.1.0"

    # --- LLM (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    # --- Appium ---
    appium_server_url: str = "http://localhost:4723"
    android_device_name: str = "emulator-5554"
    android_platform_version: str = "13"

    # --- Store Adapter Modes ---
    store_mode: Literal["mock", "real"] = "mock"
    blinkit_store_mode: Literal["mock", "real"] | None = None
    zepto_store_mode: Literal["mock", "real"] = "mock"
    instamart_store_mode: Literal["mock", "real"] = "mock"

    def is_real_store(self, store_id: str) -> bool:
        """Whether a given store should use real Appium automation."""
        if store_id == "blinkit":
            return (self.blinkit_store_mode or self.store_mode) == "real"
        if store_id == "zepto":
            return self.zepto_store_mode == "real"
        if store_id == "instamart":
            return self.instamart_store_mode == "real"
        return False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide ``Settings`` singleton.

    Cached with ``lru_cache`` rather than a manual module-level global so
    that:

    * It's still just a plain function, injectable via FastAPI's
      ``Depends(get_settings)`` — no custom container needed.
    * Tests can bypass the cache entirely by constructing ``Settings(...)``
      directly with overrides, or by calling ``get_settings.cache_clear()``.
    """

    return Settings()
