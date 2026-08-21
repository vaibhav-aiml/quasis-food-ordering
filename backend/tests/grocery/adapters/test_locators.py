"""Tests for app.grocery.adapters.locators.

These test SHAPE only — not locator correctness, which cannot be
verified without a real device (see Phase 8 docs, section 6).
"""

from app.grocery.adapters.blinkit.locators import LOCATORS as BLINKIT_LOCATORS
from app.grocery.adapters.instamart.locators import LOCATORS as INSTAMART_LOCATORS
from app.grocery.adapters.locators import (
    CheckoutLocators,
    ProductCardLocators,
    SearchScreenLocators,
    StoreLocatorConfig,
)
from app.grocery.adapters.zepto.locators import LOCATORS as ZEPTO_LOCATORS


def test_store_locator_config_constructs_with_optional_fields_omitted() -> None:
    config = StoreLocatorConfig(
        app_package="com.example.app",
        app_activity=".MainActivity",
        search=SearchScreenLocators(search_box=("id", "search")),
        product_card=ProductCardLocators(
            product_card=("id", "card"), title=("id", "title"), price=("id", "price")
        ),
    )
    assert config.search.search_submit_button is None
    assert config.product_card.eta is None
    assert config.product_card.quantity is None


def test_all_three_stores_have_locator_configs_defined() -> None:
    for locators in (ZEPTO_LOCATORS, BLINKIT_LOCATORS, INSTAMART_LOCATORS):
        assert locators.app_package
        assert locators.app_activity
        assert locators.search.search_box
        assert locators.product_card.product_card
        assert locators.product_card.title
        assert locators.product_card.price


def test_all_placeholder_values_are_unmistakably_marked() -> None:
    """Zepto and Instamart remain placeholders until inspected; Blinkit has
    verified real app package and locator definitions.
    """

    for locators in (ZEPTO_LOCATORS, INSTAMART_LOCATORS):
        assert locators.app_package.startswith("CHANGE_ME")
        assert locators.app_activity.startswith("CHANGE_ME")
        assert locators.search.search_box[1].startswith("CHANGE_ME")

    assert BLINKIT_LOCATORS.app_package == "com.grofers.customerapp"
    assert "DEFAULT" in BLINKIT_LOCATORS.app_activity or "SplashActivity" in BLINKIT_LOCATORS.app_activity
    assert not BLINKIT_LOCATORS.search.search_box[1].startswith("CHANGE_ME")


def test_checkout_locators_has_no_payment_confirmation_field() -> None:
    """Phase 14's structural safety guarantee: CheckoutLocators must
    never gain a locator for an actual payment/place-order button — this
    project must never be ABLE to automate that tap, structurally, not
    just by convention. See app.grocery.adapters._appium_order's module docstring.
    """

    fields = set(CheckoutLocators.model_fields.keys())
    assert fields == {"cart_icon", "proceed_to_checkout_button", "payment_screen_indicator"}

    dangerous_terms = (
        "pay_now", "pay_button", "place_order", "confirm_payment",
        "submit_payment", "confirm_order",
    )
    for field_name in fields:
        assert not any(term in field_name.lower() for term in dangerous_terms), field_name


def test_all_three_stores_have_cart_and_checkout_locators_configured() -> None:
    for locators in (ZEPTO_LOCATORS, BLINKIT_LOCATORS, INSTAMART_LOCATORS):
        assert locators.product_card.add_to_cart_button is not None
        assert locators.checkout is not None
        assert locators.checkout.cart_icon
        assert locators.checkout.proceed_to_checkout_button
        assert locators.checkout.payment_screen_indicator


def test_store_locator_config_backward_compatible_without_checkout() -> None:
    """Phase 8's original fixture shape (no checkout, no
    add_to_cart_button) must still construct without error — this is
    what makes Phase 14's additions backward compatible.
    """

    config = StoreLocatorConfig(
        app_package="com.example.app",
        app_activity=".MainActivity",
        search=SearchScreenLocators(search_box=("id", "search")),
        product_card=ProductCardLocators(
            product_card=("id", "card"), title=("id", "title"), price=("id", "price")
        ),
    )
    assert config.checkout is None
    assert config.product_card.add_to_cart_button is None
