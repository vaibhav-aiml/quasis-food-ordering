"""Tests for app.domain.intent.IntentRequest."""

import pytest
from pydantic import ValidationError

from app.domain.constraints import Constraints
from app.domain.intent import CLARIFICATION_CONFIDENCE_CEILING, IntentRequest
from app.domain.product import ProductRequest


def test_valid_intent_request_constructs() -> None:
    intent = IntentRequest(
        raw_text="I need onions",
        products=[ProductRequest(name="onion")],
        confidence=0.9,
    )
    assert intent.raw_text == "I need onions"
    assert len(intent.products) == 1
    assert intent.confidence == 0.9
    assert intent.needs_clarification is False
    assert intent.clarification_reason is None


def test_constraints_default_when_omitted() -> None:
    intent = IntentRequest(
        raw_text="I need onions",
        products=[ProductRequest(name="onion")],
        confidence=0.9,
    )
    assert intent.constraints == Constraints()


def test_empty_products_without_clarification_flag_is_rejected() -> None:
    """An empty product list must never silently pass as a valid, ready
    request -- this is the core invariant behind the anti-hallucination fix.
    """

    with pytest.raises(ValidationError):
        IntentRequest(raw_text="I need nothing", products=[], confidence=0.9)


def test_empty_products_with_clarification_flag_and_reason_is_valid() -> None:
    intent = IntentRequest(
        raw_text="get me something for dinner",
        products=[],
        confidence=0.15,
        needs_clarification=True,
        clarification_reason="The user did not name any specific products to buy.",
    )
    assert intent.products == []
    assert intent.needs_clarification is True


def test_clarification_without_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IntentRequest(
            raw_text="get me something for dinner",
            products=[],
            confidence=0.2,
            needs_clarification=True,
            clarification_reason="",
        )


def test_clarification_with_confidence_above_ceiling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IntentRequest(
            raw_text="get me something for dinner",
            products=[],
            confidence=CLARIFICATION_CONFIDENCE_CEILING + 0.1,
            needs_clarification=True,
            clarification_reason="Too vague.",
        )


def test_clarification_with_confidence_at_ceiling_is_valid() -> None:
    intent = IntentRequest(
        raw_text="get me something for dinner",
        products=[],
        confidence=CLARIFICATION_CONFIDENCE_CEILING,
        needs_clarification=True,
        clarification_reason="Too vague.",
    )
    assert intent.confidence == CLARIFICATION_CONFIDENCE_CEILING


def test_confidence_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IntentRequest(
            raw_text="I need onions",
            products=[ProductRequest(name="onion")],
            confidence=1.5,
        )

    with pytest.raises(ValidationError):
        IntentRequest(
            raw_text="I need onions",
            products=[ProductRequest(name="onion")],
            confidence=-0.1,
        )


def test_blank_raw_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IntentRequest(raw_text="", products=[ProductRequest(name="onion")], confidence=0.9)
