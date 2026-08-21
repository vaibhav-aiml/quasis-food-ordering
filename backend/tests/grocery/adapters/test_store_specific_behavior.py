"""Tests for behavior that's genuinely specific to each store, not part
of the shared StoreAdapter contract (see test_adapter_contract.py).
"""

from app.grocery.adapters.blinkit.adapter import BlinkitAdapter
from app.grocery.adapters.instamart.adapter import InstamartAdapter
from app.grocery.adapters.types import SearchQuery
from app.grocery.adapters.zepto.adapter import ZeptoAdapter
from app.grocery.domain.product import ProductRequest


def test_each_adapter_reports_its_own_store_id() -> None:
    assert ZeptoAdapter().get_store_id() == "zepto"
    assert BlinkitAdapter().get_store_id() == "blinkit"
    assert InstamartAdapter().get_store_id() == "instamart"


def test_stores_produce_meaningfully_different_prices_for_the_same_request() -> None:
    """Proves ranking will have something real to sort once it's built
    (Phase 11) — if all three mocks returned identical prices, ranking
    tests downstream would never be able to distinguish success from
    failure.
    """

    query = SearchQuery(products=[ProductRequest(name="onion")])

    zepto_price = ZeptoAdapter().search(query)[0].raw_price
    blinkit_price = BlinkitAdapter().search(query)[0].raw_price
    instamart_price = InstamartAdapter().search(query)[0].raw_price

    prices = {zepto_price, blinkit_price, instamart_price}
    assert len(prices) == 3  # all different


def test_stores_have_distinct_deterministic_eta_offsets() -> None:
    query = SearchQuery(products=[ProductRequest(name="onion")])

    zepto_eta = ZeptoAdapter().search(query)[0].raw_eta
    blinkit_eta = BlinkitAdapter().search(query)[0].raw_eta
    instamart_eta = InstamartAdapter().search(query)[0].raw_eta

    etas = {zepto_eta, blinkit_eta, instamart_eta}
    assert len(etas) == 3


def test_raw_price_and_eta_are_parseable_looking_strings() -> None:
    """Sanity check that mock data at least LOOKS like what Phase 9's
    real parsing logic will eventually need to handle — not a
    replacement for Phase 9's real validation.
    """

    query = SearchQuery(products=[ProductRequest(name="onion")])
    result = ZeptoAdapter().search(query)[0]

    assert result.raw_price.replace(".", "").isdigit()
    assert "mins" in result.raw_eta
