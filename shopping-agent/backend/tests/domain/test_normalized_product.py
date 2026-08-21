"""Tests for app.domain.normalized_product.NormalizedProduct."""

import pytest
from pydantic import ValidationError

from app.domain.normalized_product import NormalizedProduct


def _valid_kwargs() -> dict:
    return dict(
        store_id="zepto",
        product_name="onion",
        price_inr=42.0,
        eta_minutes=15,
        quantity=1.0,
        unit="kg",
    )


def test_valid_construction() -> None:
    product = NormalizedProduct(**_valid_kwargs())
    assert product.in_stock is True


def test_in_stock_defaults_true() -> None:
    product = NormalizedProduct(**_valid_kwargs())
    assert product.in_stock is True


def test_in_stock_can_be_set_explicitly() -> None:
    product = NormalizedProduct(**_valid_kwargs(), in_stock=False)
    assert product.in_stock is False


@pytest.mark.parametrize("field,bad_value", [
    ("price_inr", 0),
    ("price_inr", -5.0),
    ("eta_minutes", 0),
    ("eta_minutes", -1),
    ("quantity", 0),
    ("quantity", -1.0),
])
def test_non_positive_numeric_fields_rejected(field: str, bad_value) -> None:
    kwargs = _valid_kwargs()
    kwargs[field] = bad_value
    with pytest.raises(ValidationError):
        NormalizedProduct(**kwargs)


@pytest.mark.parametrize("field", ["store_id", "product_name", "unit"])
def test_blank_string_fields_rejected(field: str) -> None:
    kwargs = _valid_kwargs()
    kwargs[field] = ""
    with pytest.raises(ValidationError):
        NormalizedProduct(**kwargs)
