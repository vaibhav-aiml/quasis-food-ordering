"""Safety guard and payment boundary enforcement for food ordering automation.

Ensures the automated pipeline strictly halts before any payment step,
requiring explicit human confirmation to finalize financial transactions.
"""

import logging
import re
from typing import Any
from app.automation.actions import is_element_present, take_screenshot
from app.automation.exceptions import PaymentScreenSafetyHalt

logger = logging.getLogger("app.automation.safety_guard")

DANGEROUS_PAYMENT_PATTERNS = [
    r"pay\s*₹?\s*\d+",
    r"proceed\s*to\s*pay",
    r"pay\s*now",
    r"place\s*order",
    r"confirm\s*&\s*pay",
    r"select\s*payment\s*method",
    r"upi\s*pin",
    r"enter\s*pin",
    r"enter\s*cvv",
    r"enter\s*otp",
    r"authorize\s*payment",
]


def is_safe_to_click(element_text: str | None, element_desc: str | None = None) -> bool:
    """Evaluate whether a button or interactive element is safe to click automatically.

    Returns False if the text indicates an immediate financial or final payment commitment.
    """
    text_to_check = f"{element_text or ''} {element_desc or ''}".strip().lower()
    if not text_to_check:
        return True

    for pattern in DANGEROUS_PAYMENT_PATTERNS:
        if re.search(pattern, text_to_check, re.IGNORECASE):
            logger.warning("SAFETY TRIGGER: Blocked dangerous payment interaction on '%s'", text_to_check)
            return False

    return True


def is_payment_screen(d: Any) -> bool:
    """Inspect current screen elements to determine if a payment or checkout screen is active.

    Args:
        d: Connected uiautomator2 Device instance.

    Returns:
        True if on a payment / final checkout screen, False otherwise.
    """
    try:
        # Check against payment screen locators
        if is_element_present(d, "payment_screen_indicators", timeout=1.0):
            return True

        # Check dump hierarchy / page texts if accessible
        if hasattr(d, "xpath"):
            for keyword in ["UPI", "Google Pay", "PhonePe", "Paytm", "Credit Card", "Debit Card", "Net Banking", "Payment Options"]:
                if d.xpath(f"//*[contains(@text, '{keyword}')]").exists:
                    return True
    except Exception as e:
        logger.debug("Error checking payment screen indicators: %s", e)

    return False


def verify_safety_boundary(d: Any, current_action: str = "unknown") -> None:
    """Verify that current screen is safe to automate.

    Raises PaymentScreenSafetyHalt if a payment screen is detected.
    """
    if is_payment_screen(d):
        screenshot = take_screenshot(d)
        logger.info("SAFETY BOUNDARY REACHED during action '%s'. Halting automation for human takeover.", current_action)
        raise PaymentScreenSafetyHalt(
            message=f"Safety halt triggered during '{current_action}'. Reached payment boundary.",
            screenshot_path=screenshot,
            details={"action": current_action, "screen": "PAYMENT_GATEWAY_DETECTED"},
        )


def stop_before_payment(d: Any, plan_id: str | None = None) -> dict[str, Any]:
    """Execute the clean, sanctioned safety stop sequence before payment.

    Captures proof screenshot and generates human takeover handover details.

    Args:
        d: Connected uiautomator2 Device instance.
        plan_id: Identifier of the active order plan.

    Returns:
        Dictionary summarizing safety stop state and takeover instructions.
    """
    screenshot_path = take_screenshot(d)
    logger.info("Automation successfully halted at safety boundary. Ready for user payment.")

    return {
        "status": "STOPPED_AT_PAYMENT",
        "plan_id": plan_id,
        "screenshot_path": screenshot_path,
        "human_takeover_required": True,
        "message": (
            "Order is in cart / checkout screen with all requested items. "
            "Please review the cart and complete payment on your device."
        ),
    }
