"""Tests for app.grocery.domain.raw_product_result.RawProductResult."""

import pytest
from pydantic import ValidationError

from app.grocery.domain.raw_product_result import RawProductResult


def _valid_kwargs() -> dict:
    return dict(
        store_id="zepto",
        raw_title="onion",
        raw_price="42.00",
        raw_eta="15 mins",
        raw_quantity="1 kg",
    )


def test_valid_construction() -> None:
    result = RawProductResult(**_valid_kwargs())
    assert result.screenshot_ref is None


def test_screenshot_ref_optional_and_settable() -> None:
    result = RawProductResult(**_valid_kwargs(), screenshot_ref="/tmp/x.png")
    assert result.screenshot_ref == "/tmp/x.png"


@pytest.mark.parametrize(
    "field", ["store_id", "raw_title", "raw_price", "raw_eta", "raw_quantity"]
)
def test_blank_required_fields_are_rejected(field: str) -> None:
    kwargs = _valid_kwargs()
    kwargs[field] = ""
    with pytest.raises(ValidationError):
        RawProductResult(**kwargs)
