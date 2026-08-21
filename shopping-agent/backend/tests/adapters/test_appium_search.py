"""Tests for app.adapters._appium_search.

Requires real `selenium` installed (project dependency) since these
exercise the actual WebDriverWait polling loop via fake driver/card
objects — same approach as tests/automation/test_waits.py. Not runnable
in the offline sandbox that built this phase; every scenario here was
verified there using a hand-built, behaviorally-faithful selenium stub
instead (see Phase 8 docs for what that covered).
"""

from selenium.common.exceptions import NoSuchElementException

from app.adapters._appium_search import search_store_via_appium
from app.adapters.locators import ProductCardLocators, SearchScreenLocators, StoreLocatorConfig
from app.adapters.types import SearchQuery
from app.domain.product import ProductRequest

SEARCH_BOX = ("id", "search_box")
CARD = ("id", "card")
TITLE = ("id", "title")
PRICE = ("id", "price")
ETA = ("id", "eta")
QTY = ("id", "qty")


class _FakeTextElement:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeCard:
    def __init__(self, sub_elements: dict) -> None:
        self._sub_elements = sub_elements

    def find_element(self, by: str, value: str):
        key = (by, value)
        if key not in self._sub_elements:
            raise NoSuchElementException(str(key))
        return self._sub_elements[key]


class _FakeSearchBox:
    def __init__(self, driver: "_FakeDriver") -> None:
        self._driver = driver

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def clear(self) -> None:
        pass

    def send_keys(self, text: str) -> None:
        self._driver.typed.append(text)


class _FakeDriver:
    def __init__(self) -> None:
        self.typed: list[str] = []
        self._search_box = _FakeSearchBox(self)
        self._cards_by_query: dict[str, list] = {}

    def set_cards(self, product_name: str, cards: list) -> None:
        self._cards_by_query[product_name] = cards

    def find_element(self, by: str, value: str):
        locator = (by, value)
        if locator == SEARCH_BOX:
            return self._search_box
        if locator == CARD:
            last = self.typed[-1] if self.typed else None
            if self._cards_by_query.get(last):
                return _FakeTextElement("present")
            raise NoSuchElementException("no cards yet")
        raise AssertionError(f"unexpected top-level locator {locator}")

    def find_elements(self, by: str, value: str) -> list:
        last = self.typed[-1] if self.typed else None
        return self._cards_by_query.get(last, [])


def _locators(*, eta: tuple | None = ETA, quantity: tuple | None = QTY) -> StoreLocatorConfig:
    return StoreLocatorConfig(
        app_package="x",
        app_activity=".Y",
        search=SearchScreenLocators(search_box=SEARCH_BOX, search_submit_button=None),
        product_card=ProductCardLocators(
            product_card=CARD, title=TITLE, price=PRICE, eta=eta, quantity=quantity
        ),
    )


def test_single_product_search_extracts_all_fields() -> None:
    driver = _FakeDriver()
    driver.set_cards(
        "onion",
        [
            _FakeCard(
                {
                    TITLE: _FakeTextElement("onion"),
                    PRICE: _FakeTextElement("42.00"),
                    ETA: _FakeTextElement("15 mins"),
                    QTY: _FakeTextElement("1 kg"),
                }
            )
        ],
    )

    results = search_store_via_appium(
        driver, "zepto", _locators(), SearchQuery(products=[ProductRequest(name="onion")])
    )

    assert len(results) == 1
    result = results[0]
    assert result.store_id == "zepto"
    assert result.raw_title == "onion"
    assert result.raw_price == "42.00"
    assert result.raw_eta == "15 mins"
    assert result.raw_quantity == "1 kg"
    assert driver.typed == ["onion"]


def test_multi_product_search_performs_one_search_per_product() -> None:
    driver = _FakeDriver()
    driver.set_cards(
        "onion",
        [_FakeCard({TITLE: _FakeTextElement("onion"), PRICE: _FakeTextElement("42.00")})],
    )
    driver.set_cards(
        "curd",
        [_FakeCard({TITLE: _FakeTextElement("curd"), PRICE: _FakeTextElement("30.00")})],
    )

    results = search_store_via_appium(
        driver,
        "zepto",
        _locators(eta=None, quantity=None),
        SearchQuery(products=[ProductRequest(name="onion"), ProductRequest(name="curd")]),
    )

    assert driver.typed == ["onion", "curd"]
    assert {r.raw_title for r in results} == {"onion", "curd"}


def test_malformed_card_is_skipped_not_fatal() -> None:
    driver = _FakeDriver()
    driver.set_cards(
        "onion",
        [
            _FakeCard({TITLE: _FakeTextElement("onion")}),  # missing PRICE -> skipped
            _FakeCard({TITLE: _FakeTextElement("onion"), PRICE: _FakeTextElement("42.00")}),
        ],
    )

    results = search_store_via_appium(
        driver,
        "zepto",
        _locators(eta=None, quantity=None),
        SearchQuery(products=[ProductRequest(name="onion")]),
    )

    assert len(results) == 1
    assert results[0].raw_price == "42.00"


def test_missing_optional_locators_fall_back_to_unknown_sentinel() -> None:
    driver = _FakeDriver()
    driver.set_cards(
        "onion",
        [_FakeCard({TITLE: _FakeTextElement("onion"), PRICE: _FakeTextElement("42.00")})],
    )

    results = search_store_via_appium(
        driver,
        "zepto",
        _locators(eta=None, quantity=None),
        SearchQuery(products=[ProductRequest(name="onion")]),
    )

    assert results[0].raw_eta == "unknown"
    assert results[0].raw_quantity == "unknown"


def test_all_cards_malformed_yields_empty_results_not_a_crash() -> None:
    driver = _FakeDriver()
    driver.set_cards("onion", [_FakeCard({})])  # no fields at all

    results = search_store_via_appium(
        driver, "zepto", _locators(), SearchQuery(products=[ProductRequest(name="onion")])
    )

    assert results == []
