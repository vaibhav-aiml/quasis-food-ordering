"""Tests for app.adapters.types."""

import pytest
from pydantic import ValidationError

from app.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.domain.product import ProductRequest


def test_search_query_requires_at_least_one_product() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(products=[])


def test_search_query_valid_construction() -> None:
    query = SearchQuery(products=[ProductRequest(name="onion")])
    assert len(query.products) == 1


def test_cart_action_result_construction() -> None:
    result = CartActionResult(store_id="zepto", product_name="onion", success=True)
    assert result.message is None


def test_checkout_state_only_accepts_known_statuses() -> None:
    with pytest.raises(ValidationError):
        CheckoutState(store_id="zepto", status="not_a_real_status")

    ok = CheckoutState(store_id="zepto", status="ready_for_payment")
    assert ok.status == "ready_for_payment"
