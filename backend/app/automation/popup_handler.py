"""Dynamic popup, overlay, and system permission handler for Swiggy automation."""

import logging
import time
from typing import Any
from app.automation.actions import click_element, is_element_present, press_key

logger = logging.getLogger("app.automation.popup_handler")


def dismiss_location_popup(d: Any) -> bool:
    """Handle and grant Android system location permission dialogs."""
    if is_element_present(d, "location_allow_button", timeout=0.8):
        logger.info("Detected location permission dialog. Granting permission...")
        return click_element(d, "location_allow_button", timeout=1.0, delay_after=0.3)
    return False


def dismiss_notification_popup(d: Any) -> bool:
    """Handle Android system notification permission or Swiggy promo alerts."""
    if is_element_present(d, "notification_deny_button", timeout=0.8):
        logger.info("Detected notification permission prompt. Dismissing...")
        return click_element(d, "notification_deny_button", timeout=1.0, delay_after=0.3)
    if is_element_present(d, "notification_allow_button", timeout=0.8):
        return click_element(d, "notification_allow_button", timeout=1.0, delay_after=0.3)
    return False


def dismiss_generic_overlay(d: Any) -> bool:
    """Dismiss generic in-app promotional popups, update dialogs, or cross buttons."""
    if is_element_present(d, "generic_close_button", timeout=0.8):
        logger.info("Detected closeable overlay/popup. Dismissing...")
        return click_element(d, "generic_close_button", timeout=1.0, delay_after=0.3)
    return False


def dismiss_address_confirmation(d: Any) -> bool:
    """Confirm delivery address / location modal if prompted on home screen."""
    if is_element_present(d, "address_confirm_button", timeout=0.8):
        logger.info("Detected delivery location confirmation modal. Confirming...")
        return click_element(d, "address_confirm_button", timeout=1.0, delay_after=0.3)
    return False


def handle_all_popups(d: Any, max_attempts: int = 4) -> int:
    """Sweep and dismiss all active popups, permission prompts, and overlay dialogs.

    Args:
        d: Connected uiautomator2 Device instance.
        max_attempts: Maximum consecutive popup dismissal passes.

    Returns:
        Total number of popups dismissed.
    """
    total_dismissed = 0

    for attempt in range(1, max_attempts + 1):
        dismissed_in_pass = False

        if dismiss_location_popup(d):
            total_dismissed += 1
            dismissed_in_pass = True
            time.sleep(0.3)

        if dismiss_notification_popup(d):
            total_dismissed += 1
            dismissed_in_pass = True
            time.sleep(0.3)

        if dismiss_address_confirmation(d):
            total_dismissed += 1
            dismissed_in_pass = True
            time.sleep(0.3)

        if dismiss_generic_overlay(d):
            total_dismissed += 1
            dismissed_in_pass = True
            time.sleep(0.3)

        if not dismissed_in_pass:
            break

    if total_dismissed > 0:
        logger.info("Cleared %s popup(s) / overlay(s).", total_dismissed)
    return total_dismissed
