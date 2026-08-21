"""Zepto locator configuration.

*** PLACEHOLDER VALUES — NOT VERIFIED AGAINST THE REAL APP ***

Every value below is deliberately an obviously-fake ``CHANGE_ME_...``
string, not a plausible-looking guess. I have no way to inspect Zepto's
actual live Android app UI — its element identifiers are proprietary,
undocumented, and change across app versions. A plausible-but-wrong guess
risks being mistaken for a verified value; an unmistakably fake one
cannot be.

Before ``ZeptoAppiumAdapter`` can automate anything real:

1. Install the real Zepto app on your device/emulator.
2. Run Appium Inspector (bundled with Appium Desktop, or the standalone
   ``appium-inspector`` app) against a live session pointed at the app.
3. Inspect the search screen, one product result card, the cart screen, and
   the checkout/payment screen; note the real
   resource-ids / accessibility ids / XPaths you actually observe -- including
   the add-to-cart button, the cart icon, the proceed-to-checkout button,
   and an element that only appears once the payment screen is reached.
4. Replace every value below with what you observed.

Until step 4 is done, ``ZeptoAppiumAdapter.search()`` will fail with
``AutomationError`` wrapping an ``AutomationTimeoutError`` — that is
EXPECTED and CORRECT behavior for placeholder locators, not a bug in the
automation engine itself (which is unit-tested independently against
fakes in ``tests/adapters/test_appium_search.py``).
"""

from app.grocery.adapters.locators import (
    CheckoutLocators,
    ProductCardLocators,
    SearchScreenLocators,
    StoreLocatorConfig,
)

LOCATORS = StoreLocatorConfig(
    app_package="CHANGE_ME_zepto_app_package",
    app_activity="CHANGE_ME_zepto_main_activity",
    search=SearchScreenLocators(
        search_box=("id", "CHANGE_ME_zepto_search_box_id"),
        search_submit_button=None,  # assumed auto-search-as-you-type; verify
    ),
    product_card=ProductCardLocators(
        product_card=("id", "CHANGE_ME_zepto_product_card_id"),
        title=("id", "CHANGE_ME_zepto_product_title_id"),
        price=("id", "CHANGE_ME_zepto_product_price_id"),
        eta=None,  # verify whether Zepto shows per-card ETA or one global ETA
        quantity=("id", "CHANGE_ME_zepto_product_quantity_id"),
        add_to_cart_button=("id", "CHANGE_ME_zepto_add_to_cart_button_id"),
    ),
    checkout=CheckoutLocators(
        cart_icon=("id", "CHANGE_ME_zepto_cart_icon_id"),
        proceed_to_checkout_button=("id", "CHANGE_ME_zepto_proceed_to_checkout_id"),
        payment_screen_indicator=("id", "CHANGE_ME_zepto_payment_screen_indicator_id"),
    ),
)
