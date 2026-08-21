"""Tests for app.grocery.automation.capabilities.build_android_capabilities."""

from app.grocery.automation.capabilities import build_android_capabilities
from app.core.config import Settings


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        android_device_name="emulator-5554",
        android_platform_version="13",
    )


def test_includes_settings_derived_values() -> None:
    caps = build_android_capabilities(_settings())
    assert caps["deviceName"] == "emulator-5554"
    assert caps["platformVersion"] == "13"
    assert caps["platformName"] == "Android"
    assert caps["automationName"] == "uiautomator2"


def test_has_sane_defaults() -> None:
    caps = build_android_capabilities(_settings())
    assert caps["noReset"] is True
    assert caps["newCommandTimeout"] == 120


def test_overrides_extend_or_replace_defaults() -> None:
    caps = build_android_capabilities(
        _settings(), appPackage="com.example.app", noReset=False
    )
    assert caps["appPackage"] == "com.example.app"
    assert caps["noReset"] is False
    # Untouched defaults remain.
    assert caps["platformName"] == "Android"
