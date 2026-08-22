"""Tests for dynamic popup, overlay, and permission suppression."""

from unittest.mock import MagicMock, patch
from app.automation.popup_handler import (
    dismiss_address_confirmation,
    dismiss_generic_overlay,
    dismiss_location_popup,
    dismiss_notification_popup,
    handle_all_popups,
)


def test_handle_all_popups_dismisses_location_and_notification():
    mock_d = MagicMock()

    with patch("app.automation.popup_handler.dismiss_location_popup", side_effect=[True, False, False, False]), \
         patch("app.automation.popup_handler.dismiss_notification_popup", side_effect=[True, False, False, False]), \
         patch("app.automation.popup_handler.dismiss_address_confirmation", return_value=False), \
         patch("app.automation.popup_handler.dismiss_generic_overlay", return_value=False):

        dismissed = handle_all_popups(mock_d, max_attempts=2)
        assert dismissed == 2


def test_handle_all_popups_no_popups():
    mock_d = MagicMock()

    with patch("app.automation.popup_handler.dismiss_location_popup", return_value=False), \
         patch("app.automation.popup_handler.dismiss_notification_popup", return_value=False), \
         patch("app.automation.popup_handler.dismiss_address_confirmation", return_value=False), \
         patch("app.automation.popup_handler.dismiss_generic_overlay", return_value=False):

        dismissed = handle_all_popups(mock_d, max_attempts=2)
        assert dismissed == 0
