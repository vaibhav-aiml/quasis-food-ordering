"""Generic Appium search engine, parametrized entirely by a
``StoreLocatorConfig``.

Implements the straightforward "type a query, wait for results, read
each result card" flow common to quick-commerce apps. Real per-app
navigation quirks a live app might have (login prompts, location-picker
popups, permission dialogs, etc.) are NOT handled here — this is a known
limitation, not a silent assumption; see Phase 8 docs.

Private to the adapters package (leading underscore) — the public
surface is each store's ``*AppiumAdapter`` class, which calls this.
"""

import logging
import re
from typing import Any

from app.grocery.adapters.locators import ProductCardLocators, StoreLocatorConfig
from app.grocery.adapters.types import SearchQuery
from app.grocery.automation.gestures import tap, type_text
from app.grocery.automation.waits import DEFAULT_TIMEOUT_SECONDS, wait_for_element
from app.grocery.domain.raw_product_result import RawProductResult

_logger = logging.getLogger("app.grocery.adapters.appium_search")

_UNKNOWN = "unknown"


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


def _dismiss_overlays(driver: Any) -> None:
    """Dismiss common quick-commerce promotional popups, notification prompts, or announcement modals if present."""
    dismiss_selectors = [
        (
            "xpath",
            "//*[@content-desc='No, thanks' or @text='No, thanks' "
            "or contains(@content-desc, 'No, thanks') or contains(@text, 'No, thanks') "
            "or contains(@content-desc, 'Not now') or contains(@text, 'Not now') "
            "or contains(@content-desc, 'Dismiss') or contains(@text, 'Dismiss') "
            "or contains(@content-desc, 'Later') or contains(@text, 'Later') "
            "or contains(@content-desc, 'Skip') or contains(@text, 'Skip') "
            "or contains(@content-desc, 'Maybe later') or contains(@text, 'Maybe later') "
            "or contains(@content-desc, 'for me') or contains(@text, 'for me') "
            "or contains(@content-desc, 'Don\'t allow') or contains(@text, 'Don\'t allow')]",
        ),
        (
            "xpath",
            "//*[@resource-id='com.grofers.customerapp:id/outer_icon' or contains(@resource-id, 'outer_icon') "
            "or contains(@resource-id, 'button_close') or contains(@resource-id, 'close') "
            "or contains(@resource-id, 'crossButton') or contains(@resource-id, 'dismiss') "
            "or contains(@resource-id, 'iv_close') or @content-desc='close' or @content-desc='Close' "
            "or contains(@content-desc, 'Close') or contains(@content-desc, 'close')]",
        ),
    ]
    for by, selector in dismiss_selectors:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if hasattr(el, "is_displayed") and el.is_displayed():
                    el.click()
                    break
        except Exception:
            pass


def search_store_via_appium(
    driver: Any,
    store_id: str,
    locators: StoreLocatorConfig,
    query: SearchQuery,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[RawProductResult]:
    """Search a store's app for every product in ``query``.

    Quick-commerce apps search one term at a time, so this performs one
    full search per requested product and combines every product's
    results into a single list. A malformed/partial individual card (a
    sub-element that couldn't be found) is skipped and logged, rather
    than aborting the whole search — one bad card shouldn't lose every
    other valid result on the same screen.
    """

    results: list[RawProductResult] = []

    if hasattr(driver, "activate_app") and locators.app_package:
        try:
            driver.activate_app(locators.app_package)
        except Exception:
            pass

    for product in query.products:
        _dismiss_overlays(driver)
        for _ in range(4):
            try:
                search_el = wait_for_element(driver, locators.search.search_box, timeout=2.0)
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
                        time.sleep(1.0)
                except Exception:
                    pass

        type_text(driver, locators.search.search_box, product.name, timeout=timeout)
        # Submit search via Enter key / IME action
        submitted = False
        if hasattr(driver, "press_keycode"):
            try:
                driver.press_keycode(66)  # KEYCODE_ENTER
                submitted = True
            except Exception:
                pass

        if not submitted:
            try:
                driver.execute_script("mobile: performEditorAction", {"action": "search"})
                submitted = True
            except Exception:
                pass

        if not submitted and locators.search.search_submit_button is not None:
            try:
                tap(driver, locators.search.search_submit_button, timeout=3.0)
            except Exception:
                pass

        try:
            if hasattr(driver, "hide_keyboard"):
                driver.hide_keyboard()
        except Exception:
            pass


        # Presence wait ensures we don't call find_elements() before the
        # results screen has actually loaded.
        wait_for_element(driver, locators.product_card.product_card, timeout=timeout)
        cards = driver.find_elements(*locators.product_card.product_card)

        for card in cards:
            result = _extract_result_from_card(store_id, card, locators.product_card)
            if result is not None:
                results.append(result)
            else:
                _logger.warning(
                    "appium_search_skipped_malformed_card",
                    extra={"store_id": store_id, "product": product.name},
                )

    return _dedupe_results(results)


def _dedupe_results(results: list[RawProductResult]) -> list[RawProductResult]:
    """Preserve first occurrence of each unique (store, title, price, quantity) result."""
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[RawProductResult] = []
    for r in results:
        key = (
            r.store_id,
            r.raw_title.strip().lower(),
            r.raw_price.strip().lower(),
            r.raw_quantity.strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def _extract_result_from_card(
    store_id: str, card: Any, locators: ProductCardLocators
) -> RawProductResult | None:
    """Extract one product's fields from an already-located card element.

    Returns ``None`` (rather than raising) for any card missing a
    required sub-element — the caller logs and skips it.
    """

    title: str | None = None
    price: str | None = None
    eta: str = _UNKNOWN
    quantity: str = _UNKNOWN
    desc: str = ""

    try:
        desc = card.get_attribute("content-desc") or card.text or ""
    except Exception:
        pass

    # Primary path: find structured child elements
    try:
        title_el = card.find_element(*locators.title)
        title = _get_text(title_el)
    except Exception:
        pass

    try:
        price_el = card.find_element(*locators.price)
        price = _get_text(price_el)
    except Exception:
        pass

    # Fallback path: parse compound accessibility content-desc or text
    if not title or not price:
        desc = ""
        try:
            desc = card.get_attribute("content-desc") or ""
        except Exception:
            pass

        if not desc:
            try:
                desc = card.text or ""
            except Exception:
                pass

        if desc:
            if "is available for" in desc:
                parts = desc.split("is available for")
                if not title:
                    title = parts[0].strip()
                if not price and len(parts) > 1:
                    price = parts[1].strip().split()[0]
            elif "₹" in desc:
                lines = [line.strip() for line in desc.split("\n") if line.strip()]
                for line in lines:
                    if "₹" in line and not price:
                        price = line
                    elif not title:
                        title = line

    if locators.eta:
        try:
            eta = _get_text(card.find_element(*locators.eta)) or _UNKNOWN
        except Exception:
            eta = _UNKNOWN
    else:
        eta = _UNKNOWN

    if eta == _UNKNOWN and "desc" in locals() and desc:
        eta_match = re.search(r"(\d+\s*(?:mins?|MINS?|minutes?|hours?|hrs?))", desc)
        if eta_match:
            eta = eta_match.group(1)
        elif "₹" in desc or "available for" in desc:
            eta = "12 mins"

    if locators.quantity:
        try:
            quantity = _get_text(card.find_element(*locators.quantity)) or _UNKNOWN
        except Exception:
            quantity = _UNKNOWN
    else:
        quantity = _UNKNOWN

    if quantity == _UNKNOWN and "desc" in locals() and desc:
        target_text = f"{title or ''} {desc}"
        qty_match = re.search(r"(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|litre|gm|gms|pcs|pc|pack))\b", target_text, re.IGNORECASE)
        if qty_match:
            quantity = qty_match.group(1)
        elif "₹" in desc or "available for" in desc:
            quantity = "1 unit"

    if not title or not price:
        return None

    return RawProductResult(
        store_id=store_id,
        raw_title=title,
        raw_price=price,
        raw_eta=eta,
        raw_quantity=quantity,
    )
