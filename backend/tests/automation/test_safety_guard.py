"""Tests for safety guard and payment boundary protection."""

from unittest.mock import MagicMock, patch
import pytest

from app.automation.exceptions import PaymentScreenSafetyHalt
from app.automation.safety_guard import (
    is_payment_screen,
    is_safe_to_click,
    stop_before_payment,
    verify_safety_boundary,
)


def test_is_safe_to_click():
    assert is_safe_to_click("ADD") is True
    assert is_safe_to_click("Add Item") is True
    assert is_safe_to_click("View Cart") is True
    assert is_safe_to_click("Proceed to Pay") is False
    assert is_safe_to_click("Pay ₹350") is False
    assert is_safe_to_click("Pay Now") is False
    assert is_safe_to_click("Enter UPI PIN") is False
    assert is_safe_to_click(None) is True


def test_is_payment_screen():
    mock_d = MagicMock()
    with patch("app.automation.safety_guard.is_element_present", return_value=True):
        assert is_payment_screen(mock_d) is True

    with patch("app.automation.safety_guard.is_element_present", return_value=False):
        mock_d.xpath.return_value.exists = False
        assert is_payment_screen(mock_d) is False


def test_verify_safety_boundary_raises_on_payment_screen():
    mock_d = MagicMock()
    with patch("app.automation.safety_guard.is_payment_screen", return_value=True), \
         patch("app.automation.safety_guard.take_screenshot", return_value="/tmp/safe.png"):

        with pytest.raises(PaymentScreenSafetyHalt) as exc_info:
            verify_safety_boundary(mock_d, "checkout")

        assert "Safety halt triggered" in str(exc_info.value)
        assert exc_info.value.screenshot_path == "/tmp/safe.png"


def test_stop_before_payment_returns_handover_dict():
    mock_d = MagicMock()
    with patch("app.automation.safety_guard.take_screenshot", return_value="/tmp/safe_handover.png"):
        info = stop_before_payment(mock_d, plan_id="plan_abc")
        assert info["status"] == "STOPPED_AT_PAYMENT"
        assert info["plan_id"] == "plan_abc"
        assert info["human_takeover_required"] is True
        assert info["screenshot_path"] == "/tmp/safe_handover.png"
