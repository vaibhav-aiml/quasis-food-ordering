"""Tests for the real Appium-backed adapter classes (ZeptoAppiumAdapter,
BlinkitAppiumAdapter, InstamartAppiumAdapter).

Uses a real ``DriverManager`` (Phase 6) with an injected FAKE driver
factory — no real Appium server needed for session-lifecycle testing.
``search()`` additionally needs real ``selenium`` installed (same as
``test_appium_search.py``) since it delegates to the real search engine.
"""

import pytest
from selenium.common.exceptions import NoSuchElementException

from app.grocery.adapters.blinkit.appium_adapter import BlinkitAppiumAdapter
from app.grocery.adapters.instamart.appium_adapter import InstamartAppiumAdapter
from app.grocery.adapters.types import SearchQuery
from app.grocery.adapters.zepto.appium_adapter import ZeptoAppiumAdapter
from app.grocery.automation.driver_manager import DriverManager
from app.grocery.automation.exceptions import AutomationError
from app.core.config import Settings
from app.grocery.domain.product import ProductRequest

ADAPTER_CLASSES = [
    (ZeptoAppiumAdapter, "zepto"),
    (BlinkitAppiumAdapter, "blinkit"),
    (InstamartAppiumAdapter, "instamart"),
]


def _settings() -> Settings:
    return Settings(_env_file=None, appium_server_url="http://fake:4723")  # type: ignore[call-arg]


class _FakeSessionDriver:
    """Minimal fake for session-lifecycle tests — no find_element support."""

    def __init__(self) -> None:
        self.quit_called = False

    def quit(self) -> None:
        self.quit_called = True


class _FakeFailingSearchDriver:
    """Fake for the error-wrapping test — every element lookup fails,
    simulating placeholder locators that don't match anything real.
    """

    def __init__(self) -> None:
        self.screenshot_saved_to: str | None = None

    def quit(self) -> None:
        pass

    def find_element(self, by: str, value: str):
        raise NoSuchElementException(f"no such element: {(by, value)}")

    def get_screenshot_as_file(self, path: str) -> bool:
        self.screenshot_saved_to = path
        from pathlib import Path

        Path(path).touch()
        return True


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_get_store_id(adapter_class, store_id: str) -> None:
    manager = DriverManager(_settings(), driver_factory=lambda u, c: _FakeSessionDriver())
    adapter = adapter_class(_settings(), manager)
    assert adapter.get_store_id() == store_id


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_is_available_reflects_driver_manager_state(adapter_class, store_id: str) -> None:
    manager = DriverManager(_settings(), driver_factory=lambda u, c: _FakeSessionDriver())
    adapter = adapter_class(_settings(), manager)

    assert adapter.is_available() is False
    manager.start({})
    assert adapter.is_available() is True


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_ensure_session_starts_with_capabilities_from_locators(
    adapter_class, store_id: str
) -> None:
    created: dict = {}

    def factory(url: str, caps: dict):
        created["caps"] = caps
        return _FakeSessionDriver()

    manager = DriverManager(_settings(), driver_factory=factory)
    adapter = adapter_class(_settings(), manager)

    adapter._ensure_session()

    assert manager.is_active is True
    if store_id == "blinkit":
        assert created["caps"]["appPackage"] == "com.grofers.customerapp"
        assert "DEFAULT" in created["caps"]["appActivity"] or "SplashActivity" in created["caps"]["appActivity"]
    else:
        assert created["caps"]["appPackage"].startswith("CHANGE_ME")
        assert created["caps"]["appActivity"].startswith("CHANGE_ME")


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_ensure_session_is_idempotent(adapter_class, store_id: str) -> None:
    call_count = {"n": 0}

    def factory(url: str, caps: dict):
        call_count["n"] += 1
        return _FakeSessionDriver()

    manager = DriverManager(_settings(), driver_factory=factory)
    adapter = adapter_class(_settings(), manager)

    adapter._ensure_session()
    adapter._ensure_session()

    assert call_count["n"] == 1


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_search_wraps_failure_in_automation_error_with_screenshot_attempt(
    adapter_class, store_id: str
) -> None:
    """Simulates exactly the expected real-world outcome with today's
    placeholder locators: every element lookup fails. Confirms the
    failure is wrapped as AutomationError (not a raw Selenium exception
    leaking out) and that a screenshot capture was attempted.
    """

    fake_driver = _FakeFailingSearchDriver()
    manager = DriverManager(_settings(), driver_factory=lambda u, c: fake_driver)
    adapter = adapter_class(_settings(), manager)

    query = SearchQuery(products=[ProductRequest(name="onion")])

    with pytest.raises(AutomationError):
        adapter.search(query, timeout=0.2)  # short timeout keeps the test fast

    assert fake_driver.screenshot_saved_to is not None


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_add_to_cart_starts_session_and_delegates_to_engine(
    adapter_class, store_id: str
) -> None:
    """Phase 14: add_to_cart is now implemented for real. With today's
    placeholder locators, it's expected to fail gracefully (a typed
    CartActionResult, never an exception) — this test confirms
    delegation and session start, not success against a real app.
    """
    from app.grocery.domain.raw_product_result import RawProductResult

    fake_driver = _FakeFailingSearchDriver()
    manager = DriverManager(_settings(), driver_factory=lambda u, c: fake_driver)
    adapter = adapter_class(_settings(), manager)
    product = RawProductResult(
        store_id=store_id, raw_title="onion", raw_price="42.00",
        raw_eta="15 mins", raw_quantity="1 kg",
    )

    result = adapter.add_to_cart(product)

    assert manager.is_active is True  # _ensure_session() ran
    assert result.success is False  # placeholder locators can't succeed yet
    assert result.store_id == store_id


@pytest.mark.parametrize(
    "adapter_class,store_id", ADAPTER_CLASSES, ids=[c[1] for c in ADAPTER_CLASSES]
)
def test_checkout_starts_session_and_delegates_to_engine(
    adapter_class, store_id: str
) -> None:
    """Phase 14: checkout is now implemented for real. Same expectation
    as add_to_cart — a typed failure with today's placeholder locators,
    never an exception, and never anything resembling a payment tap
    (verified structurally/behaviorally in test_appium_order.py).
    """

    fake_driver = _FakeFailingSearchDriver()
    manager = DriverManager(_settings(), driver_factory=lambda u, c: fake_driver)
    adapter = adapter_class(_settings(), manager)

    result = adapter.checkout()

    assert manager.is_active is True
    assert result.status == "failed"  # placeholder locators can't succeed yet
    assert result.store_id == store_id
