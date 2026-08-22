"""Tests for locator catalog and strategy resolution."""

import pytest
from app.automation.locators import SWIGGY_LOCATORS, get_locator_strategies


def test_locator_catalog_completeness():
    required_keys = [
        "home_search_bar",
        "search_input",
        "restaurant_card",
        "restaurant_title",
        "dish_title",
        "dish_add_button",
        "dish_quantity_plus",
        "customization_sheet_container",
        "customization_apply_button",
        "view_cart_button",
        "floating_cart_bar",
        "cart_checkout_button",
        "payment_screen_indicators",
        "location_allow_button",
        "notification_deny_button",
    ]
    for key in required_keys:
        assert key in SWIGGY_LOCATORS, f"Missing required locator key: {key}"
        strategies = get_locator_strategies(key)
        assert len(strategies) > 0, f"Strategies for {key} must not be empty"


def test_unknown_locator_key_raises():
    with pytest.raises(KeyError):
        get_locator_strategies("non_existent_key_12345")
