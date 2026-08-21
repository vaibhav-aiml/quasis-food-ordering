"""Tests for app.shared.domain.constraints.Constraints."""

import pytest
from pydantic import ValidationError

from app.shared.domain.constraints import Constraints, Priority


def test_defaults_apply_when_nothing_stated() -> None:
    """priority defaults to None (unstated), NOT Priority.BEST_VALUE --
    defaulting is the Ranking Engine's job (Phase 11), not the domain
    model's. See Phase 4/5 design notes.
    """
    constraints = Constraints()
    assert constraints.max_delivery_minutes is None
    assert constraints.max_budget is None
    assert constraints.priority is None


def test_priority_accepts_all_enum_values() -> None:
    for value in ("cheapest", "fastest", "best_value"):
        constraints = Constraints(priority=value)
        assert constraints.priority == Priority(value)


def test_invalid_priority_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Constraints(priority="fanciest")


def test_max_delivery_minutes_must_be_at_least_one() -> None:
    with pytest.raises(ValidationError):
        Constraints(max_delivery_minutes=0)


def test_max_budget_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Constraints(max_budget=0)

    with pytest.raises(ValidationError):
        Constraints(max_budget=-100)


def test_priority_serializes_as_plain_string() -> None:
    constraints = Constraints(priority=Priority.CHEAPEST)
    assert constraints.model_dump()["priority"] == "cheapest"


def test_priority_none_is_valid() -> None:
    constraints = Constraints(priority=None)
    assert constraints.priority is None
