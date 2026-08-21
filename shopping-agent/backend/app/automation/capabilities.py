"""Builds Appium capability dicts from project ``Settings`` plus
adapter-specific overrides.

Deliberately generic — knows nothing about any specific store's app
package or activity. Store Adapters (Phase 7) supply those via keyword
overrides; this function only fills in the device/platform-level
defaults every session needs regardless of which app it targets.
"""

from typing import Any

from app.core.config import Settings


def build_android_capabilities(settings: Settings, **overrides: Any) -> dict[str, Any]:
    """Build a base Android capabilities dict, with any keyword arguments
    overriding or extending the defaults.

    Example:
        build_android_capabilities(
            settings, appPackage="com.example.app", appActivity=".MainActivity"
        )
    """

    capabilities: dict[str, Any] = {
        "platformName": "Android",
        "automationName": "uiautomator2",
        "deviceName": settings.android_device_name,
        "platformVersion": settings.android_platform_version,
        "newCommandTimeout": 120,
        "noReset": True,
        "appWaitActivity": "*",
    }
    capabilities.update(overrides)
    return capabilities
