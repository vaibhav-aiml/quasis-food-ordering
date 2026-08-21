"""Tests for app.grocery.processing.recommendation_selection.select_best_store.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase — see Phase 12 docs for the transcript.
"""

from app.shared.domain.constraints import Constraints, Priority
from app.grocery.domain.normalized_product import NormalizedProduct
from app.grocery.processing.ranking import RankingSummary, rank_search_results
from app.grocery.processing.recommendation_selection import select_best_store


def _product(store: str, name: str, price: float, eta: int) -> NormalizedProduct:
    return NormalizedProduct(
        store_id=store, product_name=name, price_inr=price, eta_minutes=eta,
        quantity=1.0, unit="kg",
    )


def _constraints(priority: Priority | None = None) -> Constraints:
    return Constraints(priority=priority, max_delivery_minutes=None, max_budget=None)


def test_clear_winner_on_total_price() -> None:
    products = [
        _product("zepto", "onion", 10, 15),
        _product("blinkit", "onion", 15, 10),
        _product("zepto", "curd", 20, 15),
        _product("blinkit", "curd", 25, 10),
    ]
    summary = rank_search_results(products, _constraints(priority=Priority.CHEAPEST))

    basket = select_best_store(summary)

    assert basket.store_id == "zepto"
    assert basket.fulfills_all_products is True
    assert basket.total_price_inr == 30.0
    assert basket.max_eta_minutes == 15


def test_completeness_beats_lower_price() -> None:
    """A store with ALL products always beats a cheaper-but-incomplete
    store, regardless of priority.
    """

    products = [
        _product("zepto", "onion", 100, 15),
        _product("zepto", "curd", 100, 15),
        _product("blinkit", "onion", 1, 15),  # much cheaper but missing curd
    ]
    summary = rank_search_results(products, _constraints(priority=Priority.CHEAPEST))

    basket = select_best_store(summary)

    assert basket.store_id == "zepto"
    assert basket.fulfills_all_products is True


def test_partial_coverage_when_no_store_has_everything() -> None:
    products = [
        _product("zepto", "onion", 10, 15),
        _product("blinkit", "curd", 20, 10),
    ]
    summary = rank_search_results(products, _constraints(priority=Priority.CHEAPEST))

    basket = select_best_store(summary)

    assert basket.fulfills_all_products is False
    assert len(basket.missing_products) == 1


def test_fastest_priority_picks_lowest_worst_case_eta() -> None:
    products = [
        _product("zepto", "onion", 10, 30),
        _product("zepto", "curd", 10, 30),
        _product("blinkit", "onion", 10, 10),
        _product("blinkit", "curd", 10, 10),
    ]
    summary = rank_search_results(products, _constraints(priority=Priority.FASTEST))

    basket = select_best_store(summary)

    assert basket.store_id == "blinkit"
    assert basket.max_eta_minutes == 10


def test_empty_rankings_returns_none() -> None:
    summary = RankingSummary(rankings={}, priority_used=Priority.BEST_VALUE, excluded_counts={})
    assert select_best_store(summary) is None


def test_all_filtered_out_returns_none() -> None:
    products = [_product("zepto", "onion", 1000, 15)]
    summary = rank_search_results(
        products, Constraints(priority=None, max_budget=1.0, max_delivery_minutes=None)
    )

    assert select_best_store(summary) is None
