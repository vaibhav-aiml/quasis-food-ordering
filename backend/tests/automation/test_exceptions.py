"""Tests for automation custom exceptions."""

from app.automation.exceptions import (
    ActionTimeoutError,
    AutomationError,
    DeviceConnectionError,
    ElementNotFoundError,
    PaymentScreenSafetyHalt,
)


def test_exception_hierarchy():
    err = ElementNotFoundError("Element not found", details={"locator": "home_search_bar"})
    assert isinstance(err, AutomationError)
    assert "home_search_bar" in str(err)


def test_payment_safety_halt():
    halt = PaymentScreenSafetyHalt(
        message="Halted before payment",
        screenshot_path="/path/to/shot.png",
        details={"screen": "PAYMENT_METHOD"},
    )
    assert isinstance(halt, AutomationError)
    assert halt.screenshot_path == "/path/to/shot.png"
    assert "Halted before payment" in str(halt)


def test_clarification_required():
    from app.automation.exceptions import ClarificationRequired

    options = [
        {"name": "Bikanervala", "address": "Indiranagar", "index": 0},
        {"name": "Bikanervala", "address": "Koramangala", "index": 1},
    ]
    err = ClarificationRequired(
        message="Multiple locations found",
        options=options,
        details={"restaurant_name": "Bikanervala"},
    )
    assert isinstance(err, AutomationError)
    assert len(err.options) == 2
    assert err.options[0]["address"] == "Indiranagar"
    assert "Multiple locations found" in str(err)

