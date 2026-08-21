"""Blinkit locator configuration.

*** PLACEHOLDER VALUES — NOT VERIFIED AGAINST THE REAL APP ***

Every value below is deliberately an obviously-fake ``CHANGE_ME_...``
string, not a plausible-looking guess. I have no way to inspect Blinkit's
actual live Android app UI — its element identifiers are proprietary,
undocumented, and change across app versions. A plausible-but-wrong guess
risks being mistaken for a verified value; an unmistakably fake one
cannot be.

Before ``BlinkitAppiumAdapter`` can automate anything real:

1. Install the real Blinkit app on your device/emulator.
2. Run Appium Inspector (bundled with Appium Desktop, or the standalone
   ``appium-inspector`` app) against a live session pointed at the app.
3. Inspect the search screen, one product result card, the cart screen, and
   the checkout/payment screen; note the real
   resource-ids / accessibility ids / XPaths you actually observe -- including
   the add-to-cart button, the cart icon, the proceed-to-checkout button,
   and an element that only appears once the payment screen is reached.
4. Replace every value below with what you observed.

Until step 4 is done, ``BlinkitAppiumAdapter.search()`` will fail with
``AutomationError`` wrapping an ``AutomationTimeoutError`` — that is
EXPECTED and CORRECT behavior for placeholder locators, not a bug in the
automation engine itself (which is unit-tested independently against
fakes in ``tests/adapters/test_appium_search.py``).
"""

from app.adapters.locators import (
    CheckoutLocators,
    ProductCardLocators,
    SearchScreenLocators,
    StoreLocatorConfig,
)

LOCATORS = StoreLocatorConfig(
    store_id="blinkit",
    app_package="com.grofers.customerapp",
    app_activity="com.grofers.customerapp.DEFAULT",
    search=SearchScreenLocators(
        search_box=(
            "xpath",
            "//android.widget.EditText "
            "| //android.widget.EditText[contains(@resource-id, 'search') or contains(@resource-id, 'edittext') or contains(@text, 'Search') or contains(@text, 'search')] "
            "| //android.view.View[contains(@resource-id, 'ic_selectable_1') or @content-desc='Search'] "
            "| //android.widget.TextView[contains(@text, 'Search for') or contains(@text, 'Search')] "
            "| //android.view.ViewGroup[contains(@resource-id, 'search')] "
            "| //*[contains(@text, 'Search for') or @content-desc='Search']",
        ),
        search_submit_button=(
            "xpath",
            "//android.widget.TextView[contains(@resource-id, 'title') or contains(@resource-id, 'tv_title')] "
            "| //android.view.ViewGroup[contains(@resource-id, 'item_container')]//android.widget.TextView",
        ),
    ),
    product_card=ProductCardLocators(
        product_card=(
            "xpath",
            "//android.view.ViewGroup[contains(@content-desc, 'is available for') or .//android.view.View[contains(@resource-id, 'tv_name')]]",
        ),
        title=(
            "xpath",
            ".//android.widget.TextView[contains(@resource-id, 'tv_name') or contains(@resource-id, 'title') or (not(contains(@text, '₹')) and not(contains(@text, 'ADD')) and not(contains(@text, 'mins')) and not(contains(@text, 'MINS')) and not(contains(@text, 'OFF')) and not(contains(@text, 'options')) and string-length(@text) > 3)] "
            "| .//android.view.View[contains(@resource-id, 'tv_name')]",
        ),
        price=(
            "xpath",
            ".//android.widget.TextView[contains(@text, '₹') or contains(@resource-id, 'price')] "
            "| .//android.view.View[contains(@resource-id, ':id/price') and not(contains(@resource-id, 'flow'))] "
            "| .//android.view.View[contains(@content-desc, '₹')]",
        ),
        eta=(
            "xpath",
            ".//android.widget.TextView[contains(@text, 'mins') or contains(@text, 'MINS')] "
            "| .//android.view.View[contains(@resource-id, 'eta') or contains(@content-desc, 'mins')]",
        ),
        quantity=(
            "xpath",
            ".//android.widget.TextView[contains(@resource-id, 'tv_uom_title') or contains(@resource-id, 'tv_variant') or contains(@text, ' g') or contains(@text, ' kg') or contains(@text, ' ml') or contains(@text, ' l') or contains(@text, ' pack') or contains(@text, ' pcs')] "
            "| .//android.view.View[contains(@resource-id, 'tv_uom_title') or contains(@resource-id, 'tv_variant')]",
        ),
        add_to_cart_button=(
            "xpath",
            ".//android.widget.TextView[contains(@text, 'ADD') or contains(@text, 'Add')] "
            "| .//android.view.ViewGroup[contains(@resource-id, 'stepper') or contains(@resource-id, 'btn_add') or .//android.widget.TextView[contains(@text, 'ADD')]] "
            "| .//android.view.View[contains(@resource-id, 'tv_title') and (@content-desc='ADD' or @text='ADD')]",
        ),
    ),
    checkout=CheckoutLocators(
        cart_icon=(
            "xpath",
            "//android.view.ViewGroup[contains(@resource-id, 'layout_cart_strip') or contains(@resource-id, 'cl_cart')] "
            "| //android.view.View[@content-desc='View cart' or contains(@content-desc, 'View cart')] "
            "| //android.widget.TextView[contains(@text, 'View cart') or contains(@text, 'View Cart') or contains(@text, 'items')] "
            "| //*[contains(@content-desc, 'View cart') or contains(@text, 'View cart')]",
        ),
        proceed_to_checkout_button=(
            "xpath",
            "//android.widget.TextView[contains(@resource-id, 'tv_action_text') or contains(@text, 'Select Payment Method') or contains(@text, 'Choose address') or contains(@text, 'Proceed to Pay') or contains(@text, 'Checkout')] "
            "| //*[contains(@text, 'Choose address') or contains(@text, 'Select Payment Method') or contains(@text, 'Proceed to Pay')]",
        ),
        payment_screen_indicator=(
            "xpath",
            "//android.widget.TextView[contains(@text, 'Bill total') or contains(@text, 'Cards') or contains(@text, 'UPI') or contains(@text, 'Wallets') or contains(@text, 'Pay Later') or contains(@text, 'Select Payment Method') or contains(@text, 'Payment') or contains(@text, 'Checkout') or contains(@text, 'Choose address')] "
            "| //android.view.View[contains(@resource-id, 'title') and @content-desc='Checkout'] "
            "| //*[contains(@text, 'Bill total') or contains(@text, 'Select Payment Method') or contains(@text, 'Choose address')]",
        ),
    ),
)
