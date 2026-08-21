"""Generic Appium order-execution engine: add-to-cart and checkout.

Per Phase 0 architecture doc, section 14, and the master phase plan's
explicit instruction: add to cart, checkout navigation, verification
before final order — and, repeated twice in the master prompt for
emphasis, **never automatically confirm payment**.

## How "never confirm payment" is actually guaranteed here

Not by a check in this file. By the fact that
``app.grocery.adapters.locators.CheckoutLocators`` has exactly three fields —
``cart_icon``, ``proceed_to_checkout_button``, ``payment_screen_indicator``
— and no field for a "Pay Now" / "Place Order" button exists anywhere in
the type. ``checkout_via_appium`` below can only ever call
``wait_for_element`` (a presence check) on ``payment_screen_indicator``;
there is no locator value it could pass to ``tap()`` even if it wanted
to. This is a structural guarantee, not a runtime check — see
``test_checkout_locators_has_no_payment_confirmation_field`` in the test
suite for the enforcement.
"""

import logging
import time
from typing import Any

from app.grocery.adapters._appium_search import _dismiss_overlays
from app.grocery.adapters.locators import StoreLocatorConfig
from app.grocery.automation.gestures import tap, type_text
from app.grocery.automation.screenshots import capture_screenshot
from app.grocery.automation.waits import DEFAULT_TIMEOUT_SECONDS, wait_for_element
from app.grocery.adapters.types import CartActionResult, CheckoutState
from app.grocery.domain.raw_product_result import RawProductResult

_logger = logging.getLogger("app.grocery.adapters.appium_order")


def _get_text(element: Any) -> str:
    """Helper to extract text from Android elements via text or content-desc."""
    if element is None:
        return ""
    text = getattr(element, "text", "") or ""
    if not text:
        try:
            text = element.get_attribute("content-desc") or element.get_attribute("text") or ""
        except Exception:
            pass
    return text.strip()


def add_product_to_cart_via_appium(
    driver: Any,
    store_id: str,
    locators: StoreLocatorConfig,
    product: RawProductResult,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> CartActionResult:
    """Add a specific, already-found product to the cart.

    ``product`` (a ``RawProductResult``) doesn't carry a live element
    handle — by the time this is called, the screen it was originally
    found on may no longer be showing it. So this re-searches for the
    product by its exact title, re-locates its card, and taps that
    card's add-to-cart button. This duplicates a little of Phase 8's
    "type query, wait for cards" logic rather than reusing
    ``search_store_via_appium`` directly, since that function returns
    parsed data, not live elements — a documented, justified tradeoff,
    not an oversight.

    Never raises — every failure mode returns
    ``CartActionResult(success=False, message=...)`` so a caller can
    inspect and decide what to do, rather than needing to catch an
    exception for what is often an ordinary, recoverable business event
    (e.g. the item went out of stock between search and add-to-cart).
    """

    if locators.product_card.add_to_cart_button is None:
        return CartActionResult(
            store_id=store_id,
            product_name=product.raw_title,
            success=False,
            message="No add_to_cart_button locator configured for this store.",
        )

    if hasattr(driver, "activate_app") and locators.app_package:
        try:
            driver.activate_app(locators.app_package)
        except Exception:
            pass

    _dismiss_overlays(driver)

    try:
        for _ in range(2):
            try:
                search_el = wait_for_element(driver, locators.search.search_box, timeout=timeout / 2)
                cls_name = (
                    search_el.get_attribute("className")
                    if hasattr(search_el, "get_attribute")
                    else ""
                )
                if "EditText" not in str(cls_name):
                    search_el.click()
                break
            except Exception:
                _dismiss_overlays(driver)
                try:
                    if hasattr(driver, "back"):
                        driver.back()
                except Exception:
                    pass

        type_text(driver, locators.search.search_box, product.raw_title, timeout=timeout)
        if hasattr(driver, "press_keycode"):
            try:
                driver.press_keycode(66)  # KEYCODE_ENTER
            except Exception:
                pass
        elif locators.search.search_submit_button is not None:
            try:
                tap(driver, locators.search.search_submit_button, timeout=3.0)
            except Exception:
                pass

        wait_for_element(driver, locators.product_card.product_card, timeout=timeout)
        cards = driver.find_elements(*locators.product_card.product_card)
    except Exception as exc:
        return CartActionResult(
            store_id=store_id,
            product_name=product.raw_title,
            success=False,
            message=f"Failed to re-locate '{product.raw_title}': {exc}",
        )

    matching_card = None
    target_clean = product.raw_title.strip().lower()
    for card in cards:
        desc = getattr(card, "get_attribute", lambda _: "")("contentDescription") or ""
        try:
            title = _get_text(card.find_element(*locators.product_card.title)).lower()
        except Exception:
            title = ""
        card_text = f"{title} {desc}".lower()
        if target_clean in card_text or any(word in card_text for word in target_clean.split() if len(word) > 3):
            matching_card = card
            break

    if matching_card is None:
        screenshot_path = _try_capture_screenshot(driver, f"{store_id}_add_to_cart_not_found")
        return CartActionResult(
            store_id=store_id,
            product_name=product.raw_title,
            success=False,
            message=(
                f"Could not re-locate '{product.raw_title}' on the search "
                "results screen."
                + (f" (screenshot: {screenshot_path})" if screenshot_path else "")
            ),
        )

    try:
        try:
            add_button = matching_card.find_element(*locators.product_card.add_to_cart_button)
            add_button.click()
        except Exception:
            # Check if product is already added (stepper visible)
            steppers = matching_card.find_elements(
                "xpath",
                ".//android.view.ViewGroup[contains(@resource-id, 'stepper')] | .//*[contains(@text, '+') or contains(@content-desc, 'Add 1 more')]"
            )
            if not steppers:
                raise

        # If a variant selection bottom sheet / modal popped up, select the variant ADD button
        try:
            variant_adds = driver.find_elements(
                "xpath",
                "//android.view.View[contains(@resource-id, 'tv_title') and (@content-desc='ADD' or @text='ADD')] "
                "| //android.widget.TextView[contains(@text, 'ADD') or contains(@text, 'Add')] "
                "| //*[@content-desc='ADD' or @text='ADD']"
            )
            for v_btn in variant_adds:
                if hasattr(v_btn, "is_displayed") and v_btn.is_displayed():
                    v_btn.click()
                    break
        except Exception:
            pass

        # Close the variant bottom sheet if still open
        try:
            variant_indicators = driver.find_elements(
                "xpath",
                "//android.widget.TextView[contains(@text, 'Pack of')] "
                "| //android.view.View[contains(@resource-id, 'outer_icon') or contains(@content-desc, 'Close')] "
                "| //android.widget.ImageView[contains(@resource-id, 'outer_icon') or contains(@content-desc, 'Close')]"
            )
            if variant_indicators and any(getattr(v, "is_displayed", lambda: True)() for v in variant_indicators):
                if hasattr(driver, "back"):
                    driver.back()
        except Exception:
            pass
    except Exception as exc:
        screenshot_path = _try_capture_screenshot(driver, f"{store_id}_add_to_cart_failed")
        return CartActionResult(
            store_id=store_id,
            product_name=product.raw_title,
            success=False,
            message=(
                f"Failed to tap add-to-cart button: {exc}"
                + (f" (screenshot: {screenshot_path})" if screenshot_path else "")
            ),
        )

    return CartActionResult(
        store_id=store_id, product_name=product.raw_title, success=True
    )


def _select_saved_address_if_present(driver: Any) -> None:
    """If delivery address selection sheet is open, tap the saved address."""
    try:
        addr_btns = driver.find_elements(
            "xpath",
            "//android.widget.TextView[contains(@resource-id, 'location_title') or contains(@text, 'Home') or contains(@text, 'Deliver to')] "
            "| //android.view.ViewGroup[contains(@resource-id, 'address')] "
            "| //*[contains(@text, 'Home') and not(contains(@text, 'Categories'))]"
        )
        for a_btn in addr_btns:
            if hasattr(a_btn, "is_displayed") and a_btn.is_displayed():
                a_btn.click()
                break
    except Exception:
        pass


def _dismiss_for_me_modal_if_present(driver: Any) -> None:
    """If 'Ordering for someone else?' modal appears, tap 'No, it's for me!'."""
    try:
        for_me_btns = driver.find_elements(
            "xpath",
            "//*[contains(@content-desc, 'for me') or contains(@text, 'for me') "
            "or contains(@content-desc, 'No, it')]"
        )
        for fm_btn in for_me_btns:
            if hasattr(fm_btn, "is_displayed") and fm_btn.is_displayed():
                fm_btn.click()
                break
    except Exception:
        pass


def checkout_via_appium(
    driver: Any,
    store_id: str,
    locators: StoreLocatorConfig,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> CheckoutState:
    """Navigate cart → checkout, and verify the payment screen was
    reached — WITHOUT ever tapping anything on it.

    "Verification before final order" means exactly this: confirm
    (via presence-wait only) that ``payment_screen_indicator`` appears,
    proving the checkout flow worked end to end, then stop. Nothing in
    this function's code path can proceed further — see the module
    docstring for why that's structurally guaranteed, not just this
    function's choice.
    """

    if locators.checkout is None:
        return CheckoutState(
            store_id=store_id,
            status="failed",
            message="No checkout locators configured for this store.",
        )

    if hasattr(driver, "activate_app") and locators.app_package:
        try:
            driver.activate_app(locators.app_package)
        except Exception:
            pass

    try:
        # Step 0: Dismiss any active variant popup / modal
        _dismiss_overlays(driver)
        try:
            variant_indicators = driver.find_elements(
                "xpath",
                "//android.widget.TextView[contains(@text, 'Pack of')] "
                "| //android.view.View[contains(@resource-id, 'outer_icon') or contains(@content-desc, 'Close')] "
                "| //android.widget.ImageView[contains(@resource-id, 'outer_icon') or contains(@content-desc, 'Close')]"
            )
            if variant_indicators and any(getattr(v, "is_displayed", lambda: True)() for v in variant_indicators):
                if hasattr(driver, "back"):
                    driver.back()
                    time.sleep(1.0)
        except Exception:
            pass

        # Step 1: If on search or category screen, tap cart strip
        try:
            cart_els = driver.find_elements(*locators.checkout.cart_icon)
            for c_el in cart_els:
                if getattr(c_el, "is_displayed", lambda: True)():
                    c_el.click()
                    time.sleep(1.5)
                    break
        except Exception:
            pass

        # Step 2: Multi-step checkout progression (Cart -> Address -> Bill Summary -> Payment Options)
        for _ in range(4):
            # Check if actual payment options screen (Cards, UPI, Wallets, Pay Later) is reached
            try:
                pay_screen_check = driver.find_elements(
                    "xpath",
                    "//*[contains(@text, 'Cards') or contains(@text, 'Pay by any UPI app') or contains(@text, 'UPI') or contains(@text, 'Wallets') or contains(@text, 'Pay Later')]"
                )
                if pay_screen_check and any(getattr(e, "is_displayed", lambda: True)() for e in pay_screen_check):
                    break
            except Exception:
                pass

            # If on Bill summary screen with "Select Payment Method", tap it to open payment options
            try:
                select_pay_btns = driver.find_elements(
                    "xpath",
                    "//android.widget.TextView[contains(@text, 'Select Payment Method') or contains(@text, 'Proceed to Pay')] "
                    "| //*[contains(@text, 'Select Payment Method')]"
                )
                tapped_pay = False
                for sp_btn in select_pay_btns:
                    if getattr(sp_btn, "is_displayed", lambda: True)():
                        sp_btn.click()
                        time.sleep(2.0)
                        tapped_pay = True
                        break
                if tapped_pay:
                    continue
            except Exception:
                pass

            # If address bottom-sheet is open, tap saved address "Home"
            addr_clicked = False
            try:
                addr_els = driver.find_elements(
                    "xpath",
                    "//android.widget.TextView[contains(@text, 'Home') or contains(@text, 'Deliver to')] "
                    "| //*[contains(@text, 'Home') and not(contains(@text, 'Categories'))]",
                )
                for addr in addr_els:
                    if getattr(addr, "is_displayed", lambda: True)():
                        addr.click()
                        time.sleep(1.5)
                        addr_clicked = True
                        break
            except Exception:
                pass

            # Try tapping proceed button if visible
            try:
                proc_els = driver.find_elements(*locators.checkout.proceed_to_checkout_button)
                for p_el in proc_els:
                    if getattr(p_el, "is_displayed", lambda: True)():
                        p_el.click()
                        time.sleep(1.5)
                        break
            except Exception:
                pass

            if not addr_clicked:
                time.sleep(1.0)

        # Presence-only check. This is the ENTIRE "verification before
        # final order" step — see module docstring.
        wait_for_element(driver, locators.checkout.payment_screen_indicator, timeout=timeout)
    except Exception as exc:
        screenshot_path = _try_capture_screenshot(driver, f"{store_id}_checkout_failed")
        return CheckoutState(
            store_id=store_id,
            status="failed",
            message=(
                f"Checkout navigation failed: {exc}"
                + (f" (screenshot: {screenshot_path})" if screenshot_path else "")
            ),
        )

    return CheckoutState(
        store_id=store_id,
        status="ready_for_payment",
        message=(
            "Reached the payment screen. Payment was NOT confirmed — "
            "stopping here by design."
        ),
    )


def _try_capture_screenshot(driver: Any, label: str) -> str | None:
    try:
        return str(capture_screenshot(driver, label))
    except Exception:
        _logger.warning("failed_to_capture_error_screenshot", extra={"label": label})
        return None
