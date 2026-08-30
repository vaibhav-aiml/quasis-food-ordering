"""Tests for automation configuration."""

import os
from unittest.mock import patch
from app.automation.config import AutomationConfig, get_automation_config


def test_default_automation_config():
    config = AutomationConfig()
    assert config.swiggy_package_name == "in.swiggy.android"
    assert config.default_timeout == 10.0
    assert config.max_retries == 3
    assert config.device_serial is None


def test_env_override_automation_config():
    get_automation_config.cache_clear()
    with patch.dict(
        os.environ,
        {
            "ANDROID_DEVICE_SERIAL": "emulator-5554",
            "SWIGGY_PACKAGE_NAME": "in.swiggy.android.staging",
            "AUTOMATION_DEFAULT_TIMEOUT": "15.0",
            "AUTOMATION_MAX_RETRIES": "5",
        },
    ):
        config = get_automation_config()
        assert config.device_serial == "emulator-5554"
        assert config.swiggy_package_name == "in.swiggy.android.staging"
        assert config.default_timeout == 15.0
        assert config.max_retries == 5
    get_automation_config.cache_clear()
