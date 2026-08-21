"""Ranking node — Phase 15: real Ranking Engine (Phase 11).

Never uses an LLM, same as the underlying app.grocery.processing.ranking module
it delegates to (structurally verified there via an AST-based test).
"""

from typing import Any

from app.shared.domain.constraints import Constraints
from app.grocery.graph.state import GraphState
from app.grocery.processing.ranking import rank_search_results


def ranking_node(state: GraphState) -> dict[str, Any]:
    intent = state["intent"]
    constraints = intent.constraints if intent else Constraints()
    requested_products = [p.name for p in intent.products] if intent and intent.products else None
    summary = rank_search_results(
        state["normalized_products"], constraints, requested_products=requested_products
    )
    return {"ranking_summary": summary}
