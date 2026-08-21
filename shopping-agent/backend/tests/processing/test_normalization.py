"""Tests for app.processing.normalization.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase (offline pydantic stub) — see Phase 10 docs for
the verification transcript, especially the compound "1 hr 30 mins" ETA
case, which a naive parser would get wrong.
"""

import pytest

from app.domain.raw_product_result import RawProductResult
from app.processing.normalization import (
    normalize_verified_results,
    parse_eta_minutes,
    parse_quantity,
)


def _result(
    store: str, title: str, price: str, eta: str, qty: str
) -> RawProductResult:
    return RawProductResult(
        store_id=store, raw_title=title, raw_price=price, raw_eta=eta, raw_quantity=qty
    )


# --- parse_eta_minutes -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("15 mins", 15),
        ("15 min", 15),
        ("20 minutes", 20),
        ("1 hr", 60),
        ("1 hour", 60),
        ("1 hr 30 mins", 90),  # the compound case a naive parser would break on
        ("2 hrs 15 min", 135),
    ],
)
def test_parse_eta_minutes_valid_formats(raw: str, expected: int) -> None:
    assert parse_eta_minutes(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("10-15 minutes", 15),  # range -> upper bound taken
        ("15-20 mins", 20),
    ],
)
def test_parse_eta_minutes_range_takes_upper_bound(raw: str, expected: int) -> None:
    assert parse_eta_minutes(raw) == expected


@pytest.mark.parametrize("raw", ["just now", "", "asap"])
def test_parse_eta_minutes_rejects_unparseable(raw: str) -> None:
    assert parse_eta_minutes(raw) is None


# --- parse_quantity -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1 kg", (1.0, "kg")),
        ("500g", (500.0, "g")),
        ("1 litre", (1.0, "litre")),
        ("2 pcs", (2.0, "pcs")),
    ],
)
def test_parse_quantity_valid_formats(raw: str, expected: tuple) -> None:
    assert parse_quantity(raw) == expected


@pytest.mark.parametrize("raw", ["no numbers here", ""])
def test_parse_quantity_rejects_unparseable(raw: str) -> None:
    assert parse_quantity(raw) is None


# --- normalize_verified_results (full integration) -------------------------------------------------------------


def test_normalize_full_scenario_mixed_valid_and_malformed() -> None:
    results = [
        _result("zepto", "Onion", "42.00", "15 mins", "1 kg"),
        _result("zepto", "Curd", "30.00", "1 hr 30 mins", "500 g"),
        _result("blinkit", "Milk", "25.00", "just now", "1 litre"),  # bad eta
        _result("instamart", "Bread", "20.00", "10 mins", "lots"),  # bad quantity
    ]

    result = normalize_verified_results(results)

    assert len(result.normalized_products) == 2
    assert len(result.issues) == 2

    onion, curd = result.normalized_products
    assert onion.product_name == "onion"
    assert onion.price_inr == 42.0
    assert onion.eta_minutes == 15
    assert onion.quantity == 1.0
    assert onion.unit == "kg"
    assert onion.in_stock is True

    assert curd.eta_minutes == 90  # compound "1 hr 30 mins" correctly combined


def test_normalize_title_is_trimmed_and_lowercased() -> None:
    results = [_result("zepto", "  ONION  ", "42.00", "15 mins", "1 kg")]

    result = normalize_verified_results(results)

    assert result.normalized_products[0].product_name == "onion"


def test_normalize_drops_whole_item_on_single_bad_field() -> None:
    """All-or-nothing: a good price and ETA don't save an item with an
    unparseable quantity — the whole item is dropped, not partially
    normalized with a fabricated quantity.
    """

    results = [_result("zepto", "Rice", "50.00", "20 mins", "unclear")]

    result = normalize_verified_results(results)

    assert result.normalized_products == []
    assert len(result.issues) == 1
    assert "quantity" in result.issues[0].detail


def test_normalize_empty_input_returns_empty_result() -> None:
    result = normalize_verified_results([])
    assert result.normalized_products == []
    assert result.issues == []
