"""Tests for app.adapters._appium_order.

Requires real `selenium` installed (project dependency) — same as
test_appium_search.py. Not runnable in the offline sandbox that built
this phase; every scenario here, including the safety-critical
checkout test, was verified there using a hand-built, behaviorally
faithful selenium stub (see Phase 14 docs).
"""

from typing import Any

from selenium.common.exceptions import NoSuchElementException

from app.adapters._appium_order import add_product_to_cart_via_appium, checkout_via_appium
from app.adapters.locators import (
    CheckoutLocators,
    ProductCardLocators,
    SearchScreenLocators,
    StoreLocatorConfig,
)
from app.domain.raw_product_result import RawProductResult

SEARCH_BOX = ("id", "search_box")
CARD = ("id", "card")
TITLE = ("id", "title")
PRICE = ("id", "price")
ADD_BTN = ("id", "add_btn")
CART_ICON = ("id", "cart_icon")
CHECKOUT_BTN = ("id", "checkout_btn")
PAYMENT_INDICATOR = ("id", "payment_indicator")


class _FakeElement:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def clear(self) -> None:
        pass

    def send_keys(self, text: str) -> None:
        pass


class _TrackedElement:
    """Tracks whether .click() was ever called — the core mechanism for
    proving the payment indicator is only ever presence-checked.
    """

    def __init__(self) -> None:
        self.click_called = False

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def click(self) -> None:
        self.click_called = True


class _FakeAddButton:
    def __init__(self) -> None:
        self.click_called = False

    def click(self) -> None:
        self.click_called = True


class _FakeCard:
    def __init__(self, title: str, add_button: "_FakeAddButton") -> None:
        self._title_el = _FakeElement(title)
        self._add_button = add_button

    def find_element(self, by: str, value: str):
        if (by, value) == TITLE:
            return self._title_el
        if (by, value) == ADD_BTN:
            return self._add_button
        raise NoSuchElementException(str((by, value)))


class _FakeSearchBox(_FakeElement):
    def __init__(self, driver: "_FakeAddToCartDriver") -> None:
        super().__init__()
        self._driver = driver

    def send_keys(self, text: str) -> None:
        self._driver.typed.append(text)


class _FakeAddToCartDriver:
    def __init__(self, cards: list) -> None:
        self.typed: list[str] = []
        self._search_box = _FakeSearchBox(self)
        self._cards = cards

    def find_element(self, by: str, value: str):
        if (by, value) == SEARCH_BOX:
            return self._search_box
        if (by, value) == CARD:
            return _FakeElement("present")
        raise NoSuchElementException(str((by, value)))

    def find_elements(self, by: str, value: str) -> list:
        return self._cards


class _FakeCheckoutDriver:
    def __init__(self) -> None:
        self.elements = {
            CART_ICON: _TrackedElement(),
            CHECKOUT_BTN: _TrackedElement(),
            PAYMENT_INDICATOR: _TrackedElement(),
        }

    def find_element(self, by: str, value: str):
        key = (by, value)
        if key not in self.elements:
            raise NoSuchElementException(str(key))
        return self.elements[key]

    def find_elements(self, by: str, value: str) -> list:
        key = (by, value)
        if key in self.elements:
            return [self.elements[key]]
        return []


def _add_to_cart_locators(add_to_cart_button=ADD_BTN) -> StoreLocatorConfig:
    return StoreLocatorConfig(
        app_package="x",
        app_activity=".Y",
        search=SearchScreenLocators(search_box=SEARCH_BOX, search_submit_button=None),
        product_card=ProductCardLocators(
            product_card=CARD, title=TITLE, price=PRICE, eta=None, quantity=None,
            add_to_cart_button=add_to_cart_button,
        ),
    )


_UNSET = object()


def _checkout_locators(checkout: Any = _UNSET) -> StoreLocatorConfig:
    """``checkout`` distinguishes "not supplied, use the default working
    config" (``_UNSET``) from "explicitly no checkout config" (``None``)
    — using bare ``None`` for both, as an earlier version of this helper
    did, made it impossible for a test to ever actually construct a
    config with ``checkout=None``, since the default and the explicit
    value were indistinguishable.
    """

    if checkout is _UNSET:
        checkout = CheckoutLocators(
            cart_icon=CART_ICON,
            proceed_to_checkout_button=CHECKOUT_BTN,
            payment_screen_indicator=PAYMENT_INDICATOR,
        )
    return StoreLocatorConfig(
        app_package="x",
        app_activity=".Y",
        search=SearchScreenLocators(search_box=SEARCH_BOX, search_submit_button=None),
        product_card=ProductCardLocators(
            product_card=CARD, title=TITLE, price=PRICE, eta=None, quantity=None
        ),
        checkout=checkout,
    )


def _product() -> RawProductResult:
    return RawProductResult(
        store_id="zepto", raw_title="onion", raw_price="42.00",
        raw_eta="15 mins", raw_quantity="1 kg",
    )


# --- add_product_to_cart_via_appium -------------------------------------------------------------


def test_add_to_cart_finds_exact_match_and_taps_its_button() -> None:
    btn = _FakeAddButton()
    driver = _FakeAddToCartDriver([_FakeCard("onion", btn), _FakeCard("curd", _FakeAddButton())])

    result = add_product_to_cart_via_appium(driver, "zepto", _add_to_cart_locators(), _product())

    assert result.success is True
    assert btn.click_called is True
    assert driver.typed == ["onion"]


def test_add_to_cart_product_not_found_on_research() -> None:
    driver = _FakeAddToCartDriver([_FakeCard("curd", _FakeAddButton())])

    result = add_product_to_cart_via_appium(driver, "zepto", _add_to_cart_locators(), _product())

    assert result.success is False
    assert "could not re-locate" in result.message.lower()


def test_add_to_cart_missing_locator_fails_cleanly() -> None:
    driver = _FakeAddToCartDriver([])

    result = add_product_to_cart_via_appium(
        driver, "zepto", _add_to_cart_locators(add_to_cart_button=None), _product()
    )

    assert result.success is False
    assert "no add_to_cart_button locator" in result.message.lower()


def test_add_to_cart_never_raises_on_failure() -> None:
    """Every failure mode returns a typed result, never an exception."""

    driver = _FakeAddToCartDriver([])  # empty -> product not found
    result = add_product_to_cart_via_appium(driver, "zepto", _add_to_cart_locators(), _product())
    assert result.success is False  # did not raise


# --- checkout_via_appium (the safety-critical function) -------------------------------------------------------------


def test_checkout_taps_cart_and_proceed_but_never_taps_payment_indicator() -> None:
    """THE core safety test for this entire phase: proves
    payment_screen_indicator is only ever presence-checked, never
    clicked, regardless of how the flow proceeds.
    """

    driver = _FakeCheckoutDriver()

    result = checkout_via_appium(driver, "zepto", _checkout_locators(), timeout=1.0)

    assert driver.elements[PAYMENT_INDICATOR].click_called is False, (
        "SAFETY VIOLATION: payment_screen_indicator was clicked"
    )
    assert driver.elements[CART_ICON].click_called is True
    assert driver.elements[CHECKOUT_BTN].click_called is True
    assert result.status == "ready_for_payment"
    assert "NOT confirmed" in result.message


def test_checkout_with_no_configured_locators_fails_cleanly() -> None:
    driver = _FakeCheckoutDriver()

    result = checkout_via_appium(driver, "zepto", _checkout_locators(checkout=None))

    assert result.status == "failed"
    assert "no checkout locators" in result.message.lower()


def test_checkout_never_raises_on_navigation_failure() -> None:
    class _BrokenDriver:
        def find_element(self, by, value):
            raise NoSuchElementException("nothing here")

    result = checkout_via_appium(_BrokenDriver(), "zepto", _checkout_locators(), timeout=0.2)

    assert result.status == "failed"  # did not raise
