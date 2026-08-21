"""Normalization node — Phase 15: real Normalization Layer (Phase 10)."""

from typing import Any

from app.graph.state import GraphState
from app.processing.normalization import normalize_verified_results


def normalization_node(state: GraphState) -> dict[str, Any]:
    verification_result = state["verification_result"]
    valid_results = verification_result.valid_results if verification_result else []
    result = normalize_verified_results(valid_results)
    return {"normalized_products": result.normalized_products}
