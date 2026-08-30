"""Device connection and lifecycle management for Android automation."""

import logging
from typing import Any
from app.automation.config import get_automation_config
from app.automation.exceptions import DeviceConnectionError, DeviceNotFoundError

logger = logging.getLogger("app.automation.device_manager")


def connect_device(serial: str | None = None) -> Any:
    """Connect to an Android device or emulator using uiautomator2.

    Args:
        serial: Optional ADB device serial or IP:port (e.g. 'emulator-5554' or '192.168.1.5:5555').
                If None, uses configuration default or auto-detects first ADB device.

    Returns:
        uiautomator2.Device instance.

    Raises:
        DeviceConnectionError: If connection fails.
    """
    config = get_automation_config()
    target_serial = serial or config.device_serial

    try:
        import uiautomator2 as u2  # type: ignore[import-untyped]
    except ImportError as e:
        raise DeviceConnectionError(
            "uiautomator2 is not installed. Please run `pip install uiautomator2`."
        ) from e

    try:
        if target_serial:
            logger.info("Connecting to Android device with serial: %s", target_serial)
            d = u2.connect(target_serial)
        else:
            logger.info("Auto-detecting and connecting to default ADB device...")
            d = u2.connect()

        # Verify connectivity by fetching basic device info
        info = d.info
        logger.info(
            "Connected to Android device successfully. Serial: %s, Model: %s, SDK: %s",
            getattr(d, "serial", target_serial or "default"),
            info.get("productName", "unknown"),
            info.get("sdkInt", "unknown"),
        )
        return d
    except Exception as e:
        error_msg = f"Failed to connect to Android device '{target_serial or 'auto'}': {e}"
        logger.error(error_msg, exc_info=True)
        raise DeviceConnectionError(error_msg) from e


def get_device_info(d: Any) -> dict[str, Any]:
    """Retrieve comprehensive hardware, OS, and display details from the connected device.

    Args:
        d: Connected uiautomator2 Device instance.

    Returns:
        Dictionary containing device metadata.
    """
    if d is None:
        raise DeviceConnectionError("Device object is None.")

    try:
        info = d.info if hasattr(d, "info") else {}
        window_size = d.window_size() if callable(getattr(d, "window_size", None)) else (0, 0)
        serial = getattr(d, "serial", "unknown")

        return {
            "serial": serial,
            "product_name": info.get("productName", "unknown"),
            "brand": info.get("brand", "unknown"),
            "model": info.get("model", "unknown"),
            "sdk_int": info.get("sdkInt", 0),
            "screen_width": window_size[0] if isinstance(window_size, tuple) else info.get("displayWidth", 0),
            "screen_height": window_size[1] if isinstance(window_size, tuple) else info.get("displayHeight", 0),
            "screen_on": info.get("screenOn", True),
            "natural_orientation": info.get("naturalOrientation", True),
        }
    except Exception as e:
        logger.warning("Error querying device info: %s", e)
        return {"serial": getattr(d, "serial", "unknown"), "error": str(e)}


def is_device_connected(d: Any) -> bool:
    """Verify if the device connection is alive and responding.

    Args:
        d: Connected uiautomator2 Device instance.

    Returns:
        True if alive, False otherwise.
    """
    if d is None:
        return False
    try:
        _ = d.info
        return True
    except Exception:
        return False


def ensure_app_installed(d: Any, package_name: str | None = None) -> bool:
    """Check if the target package (e.g. Swiggy) is installed on the device.

    Args:
        d: Connected uiautomator2 Device instance.
        package_name: Package name to verify. Defaults to Swiggy package.

    Returns:
        True if installed, False otherwise.
    """
    pkg = package_name or get_automation_config().swiggy_package_name
    if d is None:
        raise DeviceConnectionError("Device is not connected.")

    try:
        # Check via app_info if supported
        if hasattr(d, "app_info"):
            try:
                app_info = d.app_info(pkg)
                if isinstance(app_info, dict) and app_info.get("packageName") == pkg:
                    return True
            except Exception:
                pass

        if hasattr(d, "shell"):
            res = d.shell(f"pm list packages {pkg}")
            output_str = getattr(res, "output", str(res)) if res is not None else ""
            return pkg in output_str

        return False
    except Exception as e:
        logger.warning("Failed to check package installation for '%s': %s", pkg, e)
        return False


def reconnect_device(serial: str | None = None) -> Any:
    """Attempt to reconnect to the device after a disconnection."""
    logger.info("Attempting to reconnect device...")
    return connect_device(serial=serial)
