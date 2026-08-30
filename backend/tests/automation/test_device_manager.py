"""Tests for device manager connection and lifecycle utilities."""

from unittest.mock import MagicMock, patch
import pytest

from app.automation.device_manager import (
    connect_device,
    ensure_app_installed,
    get_device_info,
    is_device_connected,
)
from app.automation.exceptions import DeviceConnectionError


def test_get_device_info():
    mock_device = MagicMock()
    mock_device.info = {
        "productName": "Pixel_6",
        "brand": "Google",
        "model": "Pixel 6",
        "sdkInt": 34,
        "displayWidth": 1080,
        "displayHeight": 2400,
    }
    mock_device.serial = "emulator-5554"
    mock_device.window_size.return_value = (1080, 2400)

    info = get_device_info(mock_device)
    assert info["serial"] == "emulator-5554"
    assert info["product_name"] == "Pixel_6"
    assert info["sdk_int"] == 34
    assert info["screen_width"] == 1080
    assert info["screen_height"] == 2400


def test_is_device_connected():
    mock_device = MagicMock()
    mock_device.info = {"sdkInt": 34}
    assert is_device_connected(mock_device) is True

    failing_device = MagicMock()
    type(failing_device).info = property(lambda self: (_ for _ in ()).throw(RuntimeError("disconnected")))
    assert is_device_connected(failing_device) is False
    assert is_device_connected(None) is False


def test_ensure_app_installed():
    mock_device = MagicMock()
    mock_device.app_info.return_value = {"packageName": "in.swiggy.android"}
    assert ensure_app_installed(mock_device, "in.swiggy.android") is True

    mock_device.app_info.side_effect = Exception("Not found")
    mock_shell_res = MagicMock()
    mock_shell_res.output = "package:in.swiggy.android\npackage:com.android.settings"
    mock_device.shell.return_value = mock_shell_res
    assert ensure_app_installed(mock_device, "in.swiggy.android") is True


def test_connect_device_failure_raises():
    mock_u2 = MagicMock()
    mock_u2.connect.side_effect = Exception("ADB server not running")
    with patch.dict("sys.modules", {"uiautomator2": mock_u2}):
        with pytest.raises(DeviceConnectionError):
            connect_device(serial="non_existent_device")
