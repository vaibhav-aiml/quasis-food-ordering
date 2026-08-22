"""Custom exceptions for the food ordering automation system."""

from typing import Any


class AutomationError(Exception):
    """Base exception for all automation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class DeviceConnectionError(AutomationError):
    """Raised when connecting to an Android device fails or connection is lost."""
    pass


class DeviceNotFoundError(DeviceConnectionError):
    """Raised when no compatible Android device or emulator is detected."""
    pass


class ElementNotFoundError(AutomationError):
    """Raised when an expected UI element is not found within the timeout."""
    pass


class ActionTimeoutError(AutomationError):
    """Raised when a UI action times out."""
    pass


class PopupInterferenceError(AutomationError):
    """Raised when an unhandled popup or overlay blocks automation."""
    pass


class PaymentScreenSafetyHalt(AutomationError):
    """Raised when automation safely halts before payment screen for human takeover."""

    def __init__(
        self,
        message: str = "Safety halt: Reached payment screen. Automation stopped for user takeover.",
        screenshot_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.screenshot_path = screenshot_path


class FlowExecutionError(AutomationError):
    """Raised when a high-level user flow fails to complete."""
    pass


class OrderExecutionCancelled(AutomationError):
    """Raised when an in-progress order execution is cancelled."""
    pass
