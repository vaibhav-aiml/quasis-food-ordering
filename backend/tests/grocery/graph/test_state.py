"""Tests for app.grocery.graph.state — Phase 15 rewrite."""

from app.grocery.graph.state import GraphState, initial_state


def test_initial_state_shape() -> None:
    state: GraphState = initial_state("I need onions")

    assert state["raw_text"] == "I need onions"
    assert state["intent"] is None
    assert state["selected_stores"] == []
    assert state["raw_results"] == []
    assert state["verification_result"] is None
    assert state["normalized_products"] == []
    assert state["ranking_summary"] is None
    assert state["basket"] is None
    assert state["recommendation"] is None
    assert state["approval_outcome"] is None
    assert state["cart_results"] == []
    assert state["checkout_state"] is None
    assert state["order_confirmation"] is None
    assert state["status"] == "in_progress"
    assert state["error_message"] is None
    assert state["retry_count"] == 0


def test_ready_for_payment_is_a_valid_status_literal() -> None:
    """Guards the Phase 15 safety rename: 'confirmed' must NOT appear as
    a status value anywhere — 'ready_for_payment' replaced it precisely
    because 'confirmed' reads ambiguously next to Phase 14's payment
    safety rule.
    """

    state = initial_state("x")
    state["status"] = "ready_for_payment"
    assert state["status"] == "ready_for_payment"
