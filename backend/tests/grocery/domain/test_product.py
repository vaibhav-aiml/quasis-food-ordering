"""Tests for app.grocery.domain.product.ProductRequest."""

import pytest
from pydantic import ValidationError

from app.grocery.domain.product import ProductRequest


def test_name_is_trimmed_and_lowercased() -> None:
    product = ProductRequest(name="  Onions  ")
    assert product.name == "onions"


def test_unit_is_trimmed_and_lowercased() -> None:
    product = ProductRequest(name="curd", unit="  KG  ")
    assert product.unit == "kg"


def test_defaults_apply_when_quantity_and_unit_omitted() -> None:
    product = ProductRequest(name="onion")
    assert product.quantity == 1.0
    assert product.unit == "unit"


def test_blank_name_after_trim_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductRequest(name="   ")


def test_empty_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductRequest(name="")


def test_non_positive_quantity_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductRequest(name="onion", quantity=0)

    with pytest.raises(ValidationError):
        ProductRequest(name="onion", quantity=-1)
