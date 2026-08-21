"""Tests for app.grocery.processing.verification.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase (offline pydantic stub, no network needed) — see
Phase 9 docs for the verification transcript. This file is what actually
runs on your machine with real pydantic.
"""

import pytest

from app.grocery.domain.product import ProductRequest
from app.grocery.domain.raw_product_result import RawProductResult
from app.grocery.processing.verification import (
    detect_duplicates,
    detect_missing_products,
    detect_stores_needing_retry,
    parse_price,
    verify_prices,
    verify_search_results,
)


def _result(
    store: str, title: str, price: str, eta: str = "15 mins", qty: str = "1 kg"
) -> RawProductResult:
    return RawProductResult(
        store_id=store, raw_title=title, raw_price=price, raw_eta=eta, raw_quantity=qty
    )


def _product(name: str) -> ProductRequest:
    return ProductRequest(name=name)


# --- parse_price -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("42.00", 42.0),
        ("42", 42.0),
        ("₹42.00", 42.0),
        ("Rs. 42", 42.0),
        ("1,200.50", 1200.50),
    ],
)
def test_parse_price_handles_valid_formats(raw: str, expected: float) -> None:
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "0", "-5", "N/A"])
def test_parse_price_rejects_invalid_values(raw: str) -> None:
    assert parse_price(raw) is None


# --- verify_prices -------------------------------------------------------------


def test_verify_prices_splits_valid_and_invalid() -> None:
    results = [
        _result("zepto", "onion", "42.00"),
        _result("zepto", "curd", "N/A"),
        _result("blinkit", "onion", "0"),
    ]

    valid, issues = verify_prices(results)

    assert len(valid) == 1
    assert valid[0].raw_title == "onion" and valid[0].store_id == "zepto"
    assert len(issues) == 2
    assert all(issue.reason == "invalid_price" for issue in issues)


# --- detect_duplicates -------------------------------------------------------------


def test_detect_duplicates_keeps_first_same_store_duplicate() -> None:
    results = [
        _result("zepto", "onion", "42.00"),
        _result("zepto", "onion", "45.00"),
    ]

    kept, issues = detect_duplicates(results)

    assert len(kept) == 1
    assert kept[0].raw_price == "42.00"
    assert len(issues) == 1 and issues[0].reason == "duplicate"


def test_detect_duplicates_keeps_cross_store_repeats() -> None:
    results = [
        _result("zepto", "onion", "42.00"),
        _result("blinkit", "onion", "50.00"),
    ]

    kept, issues = detect_duplicates(results)

    assert len(kept) == 2
    assert issues == []


def test_price_validation_before_dedup_keeps_the_valid_duplicate() -> None:
    """The subtle ordering-dependent case: if the FIRST occurrence has an
    invalid price and the SECOND has a valid one, the valid one must
    survive — not whichever happened to come first in the raw list.
    """

    raw = [
        _result("zepto", "onion", "N/A"),
        _result("zepto", "onion", "42.00"),
    ]

    valid_after_price_check, _ = verify_prices(raw)
    final, _ = detect_duplicates(valid_after_price_check)

    assert len(final) == 1
    assert final[0].raw_price == "42.00"


# --- detect_missing_products -------------------------------------------------------------


def test_detect_missing_products_flags_products_with_no_results() -> None:
    requested = [_product("onion"), _product("milk")]
    valid_results = [_result("zepto", "onion", "42.00")]

    missing = detect_missing_products(requested, valid_results)

    assert missing == ["milk"]


def test_detect_missing_products_empty_when_all_found() -> None:
    requested = [_product("onion")]
    valid_results = [_result("zepto", "onion", "42.00")]

    assert detect_missing_products(requested, valid_results) == []


# --- detect_stores_needing_retry -------------------------------------------------------------


def test_detect_stores_needing_retry_flags_zero_result_stores() -> None:
    valid_results = [_result("zepto", "onion", "42.00")]

    retry_stores = detect_stores_needing_retry(
        ["zepto", "blinkit", "instamart"], valid_results
    )

    assert set(retry_stores) == {"blinkit", "instamart"}


def test_detect_stores_needing_retry_empty_when_all_contributed() -> None:
    valid_results = [
        _result("zepto", "onion", "42.00"),
        _result("blinkit", "onion", "45.00"),
    ]

    assert detect_stores_needing_retry(["zepto", "blinkit"], valid_results) == []


# --- verify_search_results (full integration) -------------------------------------------------------------


def test_verify_search_results_full_scenario() -> None:
    requested = [_product("onion"), _product("curd"), _product("milk")]
    attempted_stores = ["zepto", "blinkit", "instamart"]
    raw_results = [
        _result("zepto", "onion", "42.00"),
        _result("zepto", "onion", "43.00"),  # duplicate, dropped
        _result("zepto", "curd", "N/A"),  # invalid price, dropped
        _result("blinkit", "onion", "40.00"),
        # instamart contributes nothing -> needs retry
        # milk never appears -> missing
    ]

    result = verify_search_results(requested, attempted_stores, raw_results)

    assert len(result.valid_results) == 2
    assert {(r.store_id, r.raw_price) for r in result.valid_results} == {
        ("zepto", "42.00"),
        ("blinkit", "40.00"),
    }
    # curd's only entry was invalid-priced and dropped, so curd counts as missing too
    assert result.missing_products == ["curd", "milk"]
    assert result.stores_needing_retry == ["instamart"]

    reasons = {issue.reason for issue in result.issues}
    assert reasons == {"invalid_price", "duplicate", "missing_product", "store_unavailable"}


def test_verify_search_results_all_valid_no_issues() -> None:
    requested = [_product("onion")]
    attempted_stores = ["zepto"]
    raw_results = [_result("zepto", "onion", "42.00")]

    result = verify_search_results(requested, attempted_stores, raw_results)

    assert len(result.valid_results) == 1
    assert result.issues == []
    assert result.missing_products == []
    assert result.stores_needing_retry == []
