"""Tests for app.processing._scoring_utils.min_max_normalize."""

from app.processing._scoring_utils import min_max_normalize


def test_all_equal_values_normalize_to_zero() -> None:
    assert min_max_normalize([10, 10, 10]) == [0.0, 0.0, 0.0]


def test_varied_values_scale_correctly() -> None:
    assert min_max_normalize([10, 20, 30]) == [0.0, 0.5, 1.0]


def test_single_value_normalizes_to_zero() -> None:
    assert min_max_normalize([42]) == [0.0]
