"""Locator configuration for real Appium-backed store automation.

CRITICAL: the actual locator VALUES supplied per store (see
``app/adapters/{store}/locators.py``) are UNVERIFIED PLACEHOLDERS. Real
commercial apps' UI element identifiers cannot be known without directly
inspecting the live app via Appium Inspector — they're proprietary,
undocumented, and change across app versions. This module defines the
SHAPE of that configuration; filling in correct values is explicitly the
user's responsibility. See Phase 8 docs, section 6, for exact steps.
"""

from pydantic import BaseModel, Field

from app.grocery.automation.waits import Locator


class SearchScreenLocators(BaseModel):
    """Locators for a store's search screen."""

    search_box: Locator
    search_submit_button: Locator | None = Field(
        default=None,
        description=(
            "Tap target to submit the search, if the app doesn't "
            "auto-search as you type."
        ),
    )


class ProductCardLocators(BaseModel):
    """Locators for a single product result card, and its sub-elements.

    ``product_card`` locates every matching result on the search-results
    screen (used with ``find_elements``, plural — many matches expected).
    Every other locator here is RELATIVE — found via
    ``card.find_element(...)`` scoped to one already-located card, not the
    whole screen.
    """

    product_card: Locator
    title: Locator
    price: Locator
    eta: Locator | None = Field(
        default=None,
        description=(
            "Some apps show ETA per product card; others show a single "
            "ETA once for the whole screen/cart. None here means this "
            "store's mock config doesn't expose a per-card ETA locator."
        ),
    )
    quantity: Locator | None = None
    add_to_cart_button: Locator | None = Field(
        default=None,
        description=(
            "Tap target, relative to this card, to add this product to "
            "the cart directly from the search results screen. Optional "
            "for backward compatibility with Phase 8 fixtures that "
            "predate cart/checkout support — required in practice for "
            "app.grocery.adapters._appium_order.add_product_to_cart_via_appium "
            "to succeed."
        ),
    )


class CheckoutLocators(BaseModel):
    """Locators for navigating from cart through to (but never past) the
    payment screen.

    Deliberately exactly these three fields, and no more. There is no
    field here for a "Pay Now" / "Place Order" / "Confirm Payment"
    button — not because the code chooses not to use one, but because
    the type itself has no place to put one. This is a structural
    guarantee, not a convention: automation built against this config
    has no data path that could ever reference a real payment-
    confirmation control. Enforced by
    ``test_checkout_locators_has_no_payment_confirmation_field``.
    """

    cart_icon: Locator
    proceed_to_checkout_button: Locator
    payment_screen_indicator: Locator = Field(
        description=(
            "An element that ONLY appears once the payment screen has "
            "been reached — used exclusively with a presence-wait to "
            "verify checkout succeeded up to that point. NEVER tapped."
        )
    )


class StoreLocatorConfig(BaseModel):
    """Everything needed to open and search one store's app."""

    app_package: str
    app_activity: str
    search: SearchScreenLocators
    product_card: ProductCardLocators
    checkout: CheckoutLocators | None = Field(
        default=None,
        description=(
            "Optional for backward compatibility with Phase 8 fixtures "
            "predating cart/checkout support — required in practice for "
            "app.grocery.adapters._appium_order.checkout_via_appium to succeed."
        ),
    )
