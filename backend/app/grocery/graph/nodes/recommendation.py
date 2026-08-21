"""Recommendation Generation node — Phase 15: real basket selection
(Phase 12) + LLM-backed explanation (Phase 12).

Phase 16 addition: reads ``state["selected_indices"]`` (if present) and
threads it into ``select_best_store`` so an explicit, caller-chosen
candidate index is honored instead of always defaulting to top rank.
Nothing here changed about how basket selection works otherwise —
``selected_indices`` defaults to ``None``, which is exactly the
pre-existing behavior.
"""

from typing import Any

from app.grocery.agents.recommendation_agent import RecommendationGenerator
from app.shared.domain.constraints import Priority
from app.grocery.graph.state import GraphState
from app.grocery.processing.recommendation_selection import select_best_store


def make_recommendation_generation_node(generator: RecommendationGenerator):
    def recommendation_generation_node(state: GraphState) -> dict[str, Any]:
        summary = state["ranking_summary"]
        selected_indices = state.get("selected_indices")
        basket = select_best_store(summary, selected_indices) if summary else None
        priority = summary.priority_used if summary else Priority.BEST_VALUE
        recommendation = generator.generate(basket, priority)
        return {"basket": basket, "recommendation": recommendation}

    return recommendation_generation_node


def route_after_recommendation(state: GraphState) -> str:
    """Skip approval entirely when nothing was found — approving "no
    viable store" doesn't make sense, and Phase 13's ``process_approval``
    explicitly raises if attempted. Caught by tracing the real
    integration, not assumed in Phase 5's original (mock-driven) design.
    """

    recommendation = state["recommendation"]
    if recommendation is None or recommendation.store_id is None:
        return "failed"
    return "awaiting_approval"
