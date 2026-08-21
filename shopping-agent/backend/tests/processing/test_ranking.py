"""Tests for app.processing.ranking.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase (offline pydantic stub) — see Phase 11 docs for
the verification transcript.
"""

import ast
from pathlib import Path

from app.domain.constraints import Constraints, Priority
from app.domain.normalized_product import NormalizedProduct
from app.processing.ranking import (
    apply_hard_constraints,
    rank_products_for_one_item,
    rank_search_results,
    resolve_priority,
)


def _product(
    store: str,
    name: str = "onion",
    price: float = 10.0,
    eta: int = 15,
    in_stock: bool = True,
) -> NormalizedProduct:
    return NormalizedProduct(
        store_id=store, product_name=name, price_inr=price, eta_minutes=eta,
        quantity=1.0, unit="kg", in_stock=in_stock,
    )


def _constraints(
    priority: Priority | None = None,
    max_delivery_minutes: int | None = None,
    max_budget: float | None = None,
) -> Constraints:
    return Constraints(
        priority=priority,
        max_delivery_minutes=max_delivery_minutes,
        max_budget=max_budget,
    )


# --- resolve_priority -------------------------------------------------------------


def test_resolve_priority_defaults_none_to_best_value() -> None:
    assert resolve_priority(None) == Priority.BEST_VALUE


def test_resolve_priority_preserves_explicit_value() -> None:
    assert resolve_priority(Priority.CHEAPEST) == Priority.CHEAPEST
    assert resolve_priority(Priority.FASTEST) == Priority.FASTEST


# --- apply_hard_constraints -------------------------------------------------------------


def test_apply_hard_constraints_filters_by_delivery_time() -> None:
    products = [_product("zepto", eta=15), _product("blinkit", eta=25)]

    filtered, excluded = apply_hard_constraints(
        products, _constraints(max_delivery_minutes=20)
    )

    assert [p.store_id for p in filtered] == ["zepto"]
    assert excluded == 1


def test_apply_hard_constraints_filters_by_budget() -> None:
    products = [_product("zepto", price=10), _product("blinkit", price=20)]

    filtered, excluded = apply_hard_constraints(products, _constraints(max_budget=15))

    assert [p.store_id for p in filtered] == ["zepto"]
    assert excluded == 1


def test_apply_hard_constraints_filters_out_of_stock() -> None:
    products = [
        _product("zepto", in_stock=True),
        _product("blinkit", in_stock=False),
    ]

    filtered, excluded = apply_hard_constraints(products, _constraints())

    assert [p.store_id for p in filtered] == ["zepto"]
    assert excluded == 1


def test_apply_hard_constraints_no_constraints_filters_nothing() -> None:
    products = [_product("zepto"), _product("blinkit")]

    filtered, excluded = apply_hard_constraints(products, _constraints())

    assert len(filtered) == 2
    assert excluded == 0


def test_apply_hard_constraints_combines_multiple_filters() -> None:
    products = [
        _product("zepto", price=10, eta=15),
        _product("blinkit", price=20, eta=25),  # excluded by eta
        _product("instamart", price=5, eta=10, in_stock=False),  # excluded by stock
    ]

    filtered, excluded = apply_hard_constraints(
        products, _constraints(max_delivery_minutes=20)
    )

    assert [p.store_id for p in filtered] == ["zepto"]
    assert excluded == 2


# --- rank_products_for_one_item -------------------------------------------------------------


def test_rank_by_cheapest() -> None:
    options = [
        _product("zepto", price=10, eta=20),
        _product("blinkit", price=15, eta=10),
        _product("instamart", price=20, eta=15),
    ]

    ranked, excluded = rank_products_for_one_item(
        options, _constraints(priority=Priority.CHEAPEST)
    )

    assert [r.product.store_id for r in ranked] == ["zepto", "blinkit", "instamart"]
    assert [r.rank for r in ranked] == [1, 2, 3]
    assert excluded == 0


def test_rank_by_fastest() -> None:
    options = [
        _product("zepto", price=10, eta=20),
        _product("blinkit", price=15, eta=10),
        _product("instamart", price=20, eta=15),
    ]

    ranked, _ = rank_products_for_one_item(
        options, _constraints(priority=Priority.FASTEST)
    )

    assert [r.product.store_id for r in ranked] == ["blinkit", "instamart", "zepto"]


def test_rank_by_best_value_balances_price_and_eta() -> None:
    """zepto is cheap-but-slow, blinkit is pricey-but-fast — best_value's
    equal-weighted formula should make these roughly comparable, not
    strictly favor either dimension.
    """

    options = [
        _product("zepto", price=10, eta=20),  # cheapest, slowest
        _product("blinkit", price=20, eta=10),  # priciest, fastest
    ]

    ranked, _ = rank_products_for_one_item(
        options, _constraints(priority=Priority.BEST_VALUE)
    )

    # Symmetric tradeoff -> tied scores -> stable sort keeps original order.
    assert ranked[0].score == ranked[1].score


def test_only_rank_one_gets_a_rationale() -> None:
    options = [_product("zepto", price=10), _product("blinkit", price=20)]

    ranked, _ = rank_products_for_one_item(
        options, _constraints(priority=Priority.CHEAPEST)
    )

    assert ranked[0].rationale is not None
    assert ranked[1].rationale is None


def test_all_filtered_out_returns_empty_ranked_list() -> None:
    options = [_product("zepto", price=100), _product("blinkit", price=200)]

    ranked, excluded = rank_products_for_one_item(options, _constraints(max_budget=1.0))

    assert ranked == []
    assert excluded == 2


# --- rank_search_results (full integration) -------------------------------------------------------------


def test_rank_search_results_groups_by_product_name() -> None:
    all_products = [
        _product("zepto", name="onion", price=10, eta=15),
        _product("blinkit", name="onion", price=15, eta=10),
        _product("zepto", name="curd", price=30, eta=15),
        _product("instamart", name="curd", price=25, eta=20),
    ]

    summary = rank_search_results(all_products, _constraints(priority=Priority.CHEAPEST))

    assert set(summary.rankings.keys()) == {"onion", "curd"}
    assert [r.product.store_id for r in summary.rankings["onion"]] == ["zepto", "blinkit"]
    assert [r.product.store_id for r in summary.rankings["curd"]] == ["instamart", "zepto"]
    assert summary.priority_used == Priority.CHEAPEST


def test_rank_search_results_resolves_none_priority_end_to_end() -> None:
    all_products = [_product("zepto"), _product("blinkit")]

    summary = rank_search_results(all_products, _constraints(priority=None))

    assert summary.priority_used == Priority.BEST_VALUE


def test_rank_search_results_reports_excluded_counts_per_product() -> None:
    all_products = [
        _product("zepto", name="onion", price=10),
        _product("blinkit", name="onion", price=1000),  # excluded by budget
    ]

    summary = rank_search_results(all_products, _constraints(max_budget=50))

    assert summary.excluded_counts["onion"] == 1


# --- structural enforcement: never uses an LLM -------------------------------------------------------------


def test_ranking_never_imports_the_llm_layer() -> None:
    """Master rule: the Ranking Engine must never use an LLM. Enforced
    here structurally by scanning the actual imports in ranking.py,
    not just trusted by convention.
    """

    source = Path("app/processing/ranking.py").read_text()
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    for module in imported_modules:
        assert not module.startswith("app.core.llm"), f"ranking.py imports {module}"
        assert not module.startswith("app.agents"), f"ranking.py imports {module}"
