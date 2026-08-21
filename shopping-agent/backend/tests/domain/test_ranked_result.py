"""Tests for app.domain.ranked_result.RankedResult."""

import pytest
from pydantic import ValidationError

from app.domain.normalized_product import NormalizedProduct
from app.domain.ranked_result import RankedResult


def _product() -> NormalizedProduct:
    return NormalizedProduct(
        store_id="zepto", product_name="onion", price_inr=42.0, eta_minutes=15,
        quantity=1.0, unit="kg",
    )


def test_valid_construction() -> None:
    result = RankedResult(product=_product(), rank=1, score=42.0)
    assert result.rationale is None


def test_rank_must_be_at_least_one() -> None:
    with pytest.raises(ValidationError):
        RankedResult(product=_product(), rank=0, score=42.0)


def test_rationale_can_be_set() -> None:
    result = RankedResult(
        product=_product(), rank=1, score=42.0, rationale="Cheapest option"
    )
    assert result.rationale == "Cheapest option"
