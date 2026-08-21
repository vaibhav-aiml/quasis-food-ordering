"""Verification node — Phase 15: real Verification Layer (Phase 9)."""

from typing import Any

from app.grocery.graph.state import GraphState
from app.grocery.processing.verification import verify_search_results


def verification_node(state: GraphState) -> dict[str, Any]:
    intent = state["intent"]
    products = intent.products if intent else []
    result = verify_search_results(products, state["selected_stores"], state["raw_results"])
    return {"verification_result": result}
