"""Tests for individual node functions and routing logic in
app.graph.nodes.* — Phase 15 rewrite.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase (offline pydantic + langgraph.types.interrupt
stubs) — see Phase 15 docs for the transcript. Fake adapters here satisfy
the StoreAdapter protocol structurally, same pattern as every previous
phase's fakes.
"""

from typing import Any

from app.adapters.types import CartActionResult, CheckoutState
from app.domain.constraints import Constraints, Priority
from app.domain.intent import IntentRequest
from app.domain.normalized_product import NormalizedProduct
from app.domain.product import ProductRequest
from app.domain.ranked_result import RankedResult
from app.domain.raw_product_result import RawProductResult
from app.graph.nodes.approval import awaiting_approval_node, route_after_approval
from app.graph.nodes.normalization import normalization_node
from app.graph.nodes.order_execution import _normalized_to_raw, make_order_execution_node
from app.graph.nodes.planning import make_planning_node
from app.graph.nodes.ranking import ranking_node
from app.graph.nodes.recommendation import (
    make_recommendation_generation_node,
    route_after_recommendation,
)
from app.graph.nodes.terminal import cancelled_node, failed_node, ready_for_payment_node
from app.graph.nodes.tool_orchestration import (
    MAX_RETRIES,
    make_tool_orchestration_node,
    retry_orchestration_node,
    route_after_tool_orchestration,
)
from app.graph.nodes.verification import verification_node
from app.graph.state import initial_state
from app.processing.approval import ApprovalOutcome, ApprovalOutcomeStatus
from app.processing.ranking import RankingSummary
from app.processing.recommendation_selection import StoreBasketSummary


def _product(name: str) -> ProductRequest:
    return ProductRequest(name=name, quantity=1.0, unit="unit")


def _intent(products, constraints=None) -> IntentRequest:
    return IntentRequest(
        raw_text="x",
        products=products,
        confidence=0.9,
        constraints=constraints
        or Constraints(priority=Priority.CHEAPEST, max_delivery_minutes=None, max_budget=None),
    )


def _normalized(store: str, name: str = "onion", price: float = 10.0, eta: int = 15):
    return NormalizedProduct(
        store_id=store, product_name=name, price_inr=price, eta_minutes=eta,
        quantity=1.0, unit="kg",
    )


def _ranked(store: str, name: str = "onion", price: float = 10.0, eta: int = 15):
    return RankedResult(product=_normalized(store, name, price, eta), rank=1, score=price)


class _FakeAdapter:
    """Satisfies StoreAdapter structurally — same pattern as every prior phase."""

    def __init__(
        self,
        store_id: str,
        available: bool = True,
        results: list[RawProductResult] | None = None,
        fail_search: bool = False,
        cart_success: bool = True,
        checkout_status: str = "ready_for_payment",
    ) -> None:
        self._id = store_id
        self._available = available
        self._results = results or []
        self._fail_search = fail_search
        self._cart_success = cart_success
        self._checkout_status = checkout_status
        self.cart_calls: list[RawProductResult] = []

    def get_store_id(self) -> str:
        return self._id

    def is_available(self) -> bool:
        return self._available

    def search(self, query):
        if self._fail_search:
            raise Exception("automation failed")
        return self._results

    def add_to_cart(self, product: RawProductResult) -> CartActionResult:
        self.cart_calls.append(product)
        return CartActionResult(
            store_id=self._id, product_name=product.raw_title, success=self._cart_success
        )

    def checkout(self) -> CheckoutState:
        return CheckoutState(store_id=self._id, status=self._checkout_status, message="x")


class _FakeRecommendation:
    def __init__(self, store_id: str | None, explanation: str = "x") -> None:
        self.store_id = store_id
        self.explanation = explanation
        self.used_fallback = False
        self.basket = None


class _FakeGenerator:
    def __init__(self, store_id: str | None) -> None:
        self._store_id = store_id

    def generate(self, basket, priority):
        return _FakeRecommendation(self._store_id)


# --- planning_node -------------------------------------------------------------


def test_planning_node_selects_only_available_adapters() -> None:
    adapters = [_FakeAdapter("zepto"), _FakeAdapter("blinkit", available=False)]
    node = make_planning_node(adapters)
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])

    result = node(state)

    assert result["selected_stores"] == ["zepto"]


def test_planning_node_handles_no_intent() -> None:
    node = make_planning_node([_FakeAdapter("zepto")])
    state = initial_state("x")

    result = node(state)

    assert result["selected_stores"] == []


# --- tool_orchestration_node + routing -------------------------------------------------------------


def test_tool_orchestration_node_continues_past_failed_store() -> None:
    raw_onion = RawProductResult(
        store_id="zepto", raw_title="onion", raw_price="10.00",
        raw_eta="15 mins", raw_quantity="1 kg",
    )
    adapters_by_id = {
        "zepto": _FakeAdapter("zepto", results=[raw_onion]),
        "blinkit": _FakeAdapter("blinkit", fail_search=True),
    }
    node = make_tool_orchestration_node(adapters_by_id)
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])
    state["selected_stores"] = ["zepto", "blinkit"]

    result = node(state)

    assert len(result["raw_results"]) == 1


def test_route_after_tool_orchestration_all_branches() -> None:
    assert route_after_tool_orchestration({"raw_results": ["x"], "retry_count": 0}) == "verification"
    assert route_after_tool_orchestration({"raw_results": [], "retry_count": 0}) == "retry_orchestration"
    assert route_after_tool_orchestration({"raw_results": [], "retry_count": MAX_RETRIES}) == "failed"


def test_retry_orchestration_node_increments_count() -> None:
    assert retry_orchestration_node({"retry_count": 1})["retry_count"] == 2


# --- verification -> normalization -> ranking chain -------------------------------------------------------------


def test_verification_normalization_ranking_chain() -> None:
    raw_onion = RawProductResult(
        store_id="zepto", raw_title="onion", raw_price="10.00",
        raw_eta="15 mins", raw_quantity="1 kg",
    )
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])
    state["selected_stores"] = ["zepto"]
    state["raw_results"] = [raw_onion]

    state.update(verification_node(state))
    state.update(normalization_node(state))
    ranking_result = ranking_node(state)

    assert len(state["normalized_products"]) == 1
    assert state["normalized_products"][0].product_name == "onion"
    assert "onion" in ranking_result["ranking_summary"].rankings


# --- recommendation_generation_node + routing -------------------------------------------------------------


def test_recommendation_generation_node_produces_basket_and_recommendation() -> None:
    summary = RankingSummary(
        rankings={"onion": [_ranked("zepto")]},
        priority_used=Priority.CHEAPEST,
        excluded_counts={"onion": 0},
    )
    node = make_recommendation_generation_node(_FakeGenerator("zepto"))
    state = initial_state("x")
    state["ranking_summary"] = summary

    result = node(state)

    assert result["basket"].store_id == "zepto"
    assert result["recommendation"].store_id == "zepto"


def test_route_after_recommendation_found_vs_not_found() -> None:
    assert route_after_recommendation({"recommendation": _FakeRecommendation("zepto")}) == "awaiting_approval"
    assert route_after_recommendation({"recommendation": _FakeRecommendation(None)}) == "failed"
    assert route_after_recommendation({"recommendation": None}) == "failed"


# --- awaiting_approval_node + routing (requires real langgraph.types.interrupt) -------------------------------------------------------------


def test_approval_approved_proceeds_to_order_execution(monkeypatch) -> None:
    import app.graph.nodes.approval as approval_module

    monkeypatch.setattr(
        approval_module, "interrupt", lambda payload: {"decision": "approved"}
    )
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])
    state["recommendation"] = _FakeRecommendation("zepto")

    result = awaiting_approval_node(state)

    assert result["approval_outcome"].status == ApprovalOutcomeStatus.PROCEED_TO_ORDER
    assert route_after_approval({"approval_outcome": result["approval_outcome"]}) == "order_execution"


def test_approval_modify_raw_text_routes_to_intent_understanding(monkeypatch) -> None:
    import app.graph.nodes.approval as approval_module

    monkeypatch.setattr(
        approval_module,
        "interrupt",
        lambda payload: {
            "decision": "modify",
            "modify_request": {"updated_raw_text": "I need milk instead"},
        },
    )
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])
    state["recommendation"] = _FakeRecommendation("zepto")

    result = awaiting_approval_node(state)

    assert result["raw_text"] == "I need milk instead"
    assert route_after_approval({"approval_outcome": result["approval_outcome"]}) == "intent_understanding"


def test_approval_modify_constraints_only_routes_to_planning(monkeypatch) -> None:
    import app.graph.nodes.approval as approval_module

    monkeypatch.setattr(
        approval_module,
        "interrupt",
        lambda payload: {"decision": "modify", "modify_request": {"updated_max_budget": 100.0}},
    )
    state = initial_state("x")
    state["intent"] = _intent(
        [_product("onion")],
        constraints=Constraints(priority=Priority.CHEAPEST, max_delivery_minutes=None, max_budget=None),
    )
    state["recommendation"] = _FakeRecommendation("zepto")

    result = awaiting_approval_node(state)

    assert route_after_approval({"approval_outcome": result["approval_outcome"]}) == "planning"
    assert result["intent"].constraints.max_budget == 100.0
    assert result["intent"].constraints.priority == Priority.CHEAPEST  # preserved


def test_approval_rejected_routes_to_cancelled(monkeypatch) -> None:
    import app.graph.nodes.approval as approval_module

    monkeypatch.setattr(
        approval_module, "interrupt", lambda payload: {"decision": "rejected"}
    )
    state = initial_state("x")
    state["intent"] = _intent([_product("onion")])
    state["recommendation"] = _FakeRecommendation("zepto")

    result = awaiting_approval_node(state)

    assert route_after_approval({"approval_outcome": result["approval_outcome"]}) == "cancelled"


# --- order_execution_node -------------------------------------------------------------


def _order_outcome(store_id: str = "zepto") -> ApprovalOutcome:
    return ApprovalOutcome(
        status=ApprovalOutcomeStatus.PROCEED_TO_ORDER,
        store_id=store_id, updated_constraints=None, updated_raw_text=None, message="x",
    )


def _basket(store_id: str = "zepto") -> StoreBasketSummary:
    return StoreBasketSummary(
        store_id=store_id, matched_products=[_ranked(store_id)], missing_products=[],
        total_price_inr=10.0, max_eta_minutes=15, fulfills_all_products=True,
    )


def test_order_execution_success_reaches_ready_for_payment() -> None:
    node = make_order_execution_node({"zepto": _FakeAdapter("zepto")})
    state = initial_state("x")
    state["approval_outcome"] = _order_outcome()
    state["basket"] = _basket()

    result = node(state)

    assert result["status"] == "ready_for_payment"
    assert result["order_confirmation"]["store_id"] == "zepto"


def test_order_execution_cart_failure_yields_failed_with_message() -> None:
    node = make_order_execution_node({"zepto": _FakeAdapter("zepto", cart_success=False)})
    state = initial_state("x")
    state["approval_outcome"] = _order_outcome()
    state["basket"] = _basket()

    result = node(state)

    assert result["status"] == "failed"
    assert "onion" in result["error_message"]


def test_order_execution_checkout_failure_is_not_ready_for_payment() -> None:
    node = make_order_execution_node({"zepto": _FakeAdapter("zepto", checkout_status="failed")})
    state = initial_state("x")
    state["approval_outcome"] = _order_outcome()
    state["basket"] = _basket()

    result = node(state)

    assert result["status"] == "failed"


def test_order_execution_no_basket_fails_cleanly() -> None:
    node = make_order_execution_node({"zepto": _FakeAdapter("zepto")})
    state = initial_state("x")
    state["approval_outcome"] = _order_outcome()
    state["basket"] = None

    result = node(state)

    assert result["status"] == "failed"


def test_normalized_to_raw_bridge() -> None:
    normalized = _normalized("zepto", name="onion", price=42.5, eta=15)

    raw = _normalized_to_raw(normalized)

    assert raw.store_id == "zepto"
    assert raw.raw_title == "onion"
    assert raw.raw_price == "42.50"
    assert raw.raw_eta == "15 mins"


# --- terminal nodes -------------------------------------------------------------


def test_terminal_nodes_use_ready_for_payment_not_confirmed() -> None:
    assert ready_for_payment_node({})["status"] == "ready_for_payment"
    assert cancelled_node({})["status"] == "cancelled"
    assert failed_node({"error_message": None})["status"] == "failed"
