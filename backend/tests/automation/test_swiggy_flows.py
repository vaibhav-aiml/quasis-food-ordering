"""Tests for Swiggy domain automation flows."""

from unittest.mock import MagicMock, patch
import pytest

from app.automation.swiggy_flows import (
    add_to_cart,
    launch_swiggy,
    proceed_to_checkout,
    search_menu_item,
    search_restaurant,
    select_restaurant,
    view_cart,
)


def test_launch_swiggy_success():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.handle_all_popups", return_value=0), \
         patch("app.automation.swiggy_flows.is_element_present", return_value=True):

        success = launch_swiggy(mock_d, force_stop_first=False)
        assert success is True
        mock_d.app_start.assert_called_once()


def test_search_restaurant_success():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.click_element", return_value=True), \
         patch("app.automation.swiggy_flows.set_text", return_value=True), \
         patch("app.automation.swiggy_flows.handle_all_popups", return_value=0):

        success = search_restaurant(mock_d, query="Domino's Pizza")
        assert success is True


def test_select_restaurant_success():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.scroll_to_element", return_value=MagicMock()), \
         patch("app.automation.swiggy_flows.click_element", return_value=True), \
         patch("app.automation.swiggy_flows.handle_all_popups", return_value=0):

        success = select_restaurant(mock_d, restaurant_name="Domino's Pizza")
        assert success is True


def test_search_menu_item_success():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.scroll_to_element", return_value=MagicMock()):
        success = search_menu_item(mock_d, item_name="Margherita Pizza")
        assert success is True


def test_add_to_cart_with_customizations_and_quantity():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.scroll_to_element", return_value=MagicMock()), \
         patch("app.automation.swiggy_flows.click_element", return_value=True), \
         patch("app.automation.swiggy_flows.is_element_present", side_effect=[
             True,   # dish_add_button
             True,   # customization_sheet_container
             True,   # floating_cart_bar
         ]), \
         patch("app.automation.swiggy_flows.handle_all_popups", return_value=0):

        success = add_to_cart(
            mock_d,
            item_name="Margherita Pizza",
            quantity=2,
            customizations=["Cheese Burst", "Medium 10 inch"],
        )
        assert success is True


def test_view_cart_success():
    mock_d = MagicMock()
    with patch("app.automation.swiggy_flows.click_element", return_value=True), \
         patch("app.automation.swiggy_flows.handle_all_popups", return_value=0):

        success = view_cart(mock_d)
        assert success is True


def test_proceed_to_checkout_safely_halts_at_payment():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.text = "Select Address & Pay"

    with patch("app.automation.swiggy_flows.is_payment_screen", return_value=False), \
         patch("app.automation.swiggy_flows.find_element", return_value=mock_elem), \
         patch("app.automation.swiggy_flows.click_element", return_value=True), \
         patch("app.automation.swiggy_flows.handle_all_popups", return_value=0), \
         patch("app.automation.swiggy_flows.stop_before_payment", return_value={"status": "STOPPED_AT_PAYMENT"}):

        result = proceed_to_checkout(mock_d, stop_at_payment=True)
        assert result["status"] == "STOPPED_AT_PAYMENT"
