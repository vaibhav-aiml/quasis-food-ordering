"""Automation configuration and settings."""

from functools import lru_cache
import os
from pydantic import BaseModel, Field


class AutomationConfig(BaseModel):
    """Configuration options for device automation and Swiggy flows."""

    # Package & Activity
    swiggy_package_name: str = Field(
        default="in.swiggy.android",
        description="Target Android package name for Swiggy.",
    )
    swiggy_main_activity: str = Field(
        default="in.swiggy.android.activities.HomeActivity",
        description="Main launcher activity for Swiggy.",
    )

    # Timeouts (in seconds)
    default_timeout: float = Field(
        default=10.0,
        description="Default wait timeout for UI elements.",
    )
    short_timeout: float = Field(
        default=3.0,
        description="Short wait timeout for quick lookups or popup checks.",
    )
    long_timeout: float = Field(
        default=25.0,
        description="Long wait timeout for app launch, network calls, and page transitions.",
    )
    screen_transition_timeout: float = Field(
        default=15.0,
        description="Wait timeout for full screen transitions.",
    )

    # Retries and Delays
    max_retries: int = Field(
        default=3,
        description="Default number of retry attempts for resilient actions.",
    )
    retry_backoff_factor: float = Field(
        default=1.5,
        description="Multiplicative backoff factor between retries.",
    )
    poll_interval: float = Field(
        default=0.5,
        description="Polling interval when waiting for UI state changes.",
    )
    action_delay: float = Field(
        default=0.4,
        description="Brief pause after performing an action to let UI settle.",
    )

    # Scrolling & Gestures
    scroll_swipe_distance: float = Field(
        default=0.4,
        description="Normalized swipe distance (percentage of screen height).",
    )
    max_scroll_attempts: int = Field(
        default=6,
        description="Maximum swipe iterations before failing to locate an element.",
    )

    # Device & Environment
    device_serial: str | None = Field(
        default=None,
        description="Specific Android device serial or IP:port. None means auto-detect.",
    )
    screenshots_dir: str = Field(
        default="screenshots/automation",
        description="Directory where debug and safety screenshots are stored.",
    )
    enable_debug_logging: bool = Field(
        default=True,
        description="Whether to emit verbose automation print/log statements.",
    )


@lru_cache
def get_automation_config() -> AutomationConfig:
    """Return cached AutomationConfig populated from environment variables if present."""
    device_serial = os.getenv("ANDROID_DEVICE_SERIAL") or os.getenv("DEVICE_SERIAL")
    pkg = os.getenv("SWIGGY_PACKAGE_NAME", "in.swiggy.android")
    def_timeout = float(os.getenv("AUTOMATION_DEFAULT_TIMEOUT", "10.0"))
    max_retries = int(os.getenv("AUTOMATION_MAX_RETRIES", "3"))

    return AutomationConfig(
        swiggy_package_name=pkg,
        device_serial=device_serial,
        default_timeout=def_timeout,
        max_retries=max_retries,
    )
