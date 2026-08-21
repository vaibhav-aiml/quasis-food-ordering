"""Shared conformance tests every StoreAdapter implementation must pass.

Industry practice: rather than writing three near-duplicate test files
(one per adapter), a single parametrized suite asserts the CONTRACT every
implementation promises — this is what "every adapter must expose the
same interface" (master rule #6) actually looks like as an executable
test, not just a docstring claim. Store-specific behavior (distinct
pricing) is tested separately in test_store_specific_behavior.py — this
file only tests what should be true of ANY conforming adapter, including
ones that don't exist yet (a real Appium-backed adapter in Phase 8 should
pass every test in this file unchanged).
"""

import pytest

from app.grocery.adapters.base import StoreAdapter
from app.grocery.adapters.blinkit.adapter import BlinkitAdapter
from app.grocery.adapters.instamart.adapter import InstamartAdapter
from app.grocery.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.grocery.adapters.zepto.adapter import ZeptoAdapter
from app.grocery.domain.product import ProductRequest
from app.grocery.domain.raw_product_result import RawProductResult


def _all_adapters() -> list[StoreAdapter]:
    # Fresh instances per call (not a module-level constant) so no state
    # accidentally leaks between tests, even though these mocks happen to
    # be stateless today.
    return [ZeptoAdapter(), BlinkitAdapter(), InstamartAdapter()]


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_adapter_satisfies_store_adapter_protocol(adapter: StoreAdapter) -> None:
    assert isinstance(adapter, StoreAdapter)


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_get_store_id_returns_nonempty_string(adapter: StoreAdapter) -> None:
    store_id = adapter.get_store_id()
    assert isinstance(store_id, str) and store_id


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_is_available_returns_true_for_mock_adapter(adapter: StoreAdapter) -> None:
    assert adapter.is_available() is True


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_search_returns_one_result_per_product_stamped_with_store_id(
    adapter: StoreAdapter,
) -> None:
    query = SearchQuery(
        products=[ProductRequest(name="onion"), ProductRequest(name="curd")]
    )

    results = adapter.search(query)

    assert len(results) == 2
    assert all(isinstance(r, RawProductResult) for r in results)
    assert all(r.store_id == adapter.get_store_id() for r in results)
    assert {r.raw_title for r in results} == {"onion", "curd"}


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_search_is_deterministic(adapter: StoreAdapter) -> None:
    query = SearchQuery(products=[ProductRequest(name="onion")])

    first = adapter.search(query)
    second = adapter.search(query)

    assert [r.raw_price for r in first] == [r.raw_price for r in second]


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_add_to_cart_returns_cart_action_result(adapter: StoreAdapter) -> None:
    query = SearchQuery(products=[ProductRequest(name="onion")])
    [result] = adapter.search(query)

    cart_result = adapter.add_to_cart(result)

    assert isinstance(cart_result, CartActionResult)
    assert cart_result.store_id == adapter.get_store_id()
    assert cart_result.success is True


@pytest.mark.parametrize("adapter", _all_adapters(), ids=lambda a: a.get_store_id())
def test_checkout_returns_checkout_state(adapter: StoreAdapter) -> None:
    state = adapter.checkout()

    assert isinstance(state, CheckoutState)
    assert state.store_id == adapter.get_store_id()
