"""Terminal nodes — each just finalizes ``status`` before the graph ends.

Kept as trivial, explicit nodes (rather than setting status inline at the
edges) so each terminal state has one clear place future phases can hang
side effects off.

``ready_for_payment_node`` (renamed from Phase 5's ``confirmed_node``) is
the successful-completion terminal — see ``GraphStatus``'s docstring in
``app.graph.state`` for why the rename matters.
"""

from typing import Any

from app.graph.state import GraphState


def ready_for_payment_node(state: GraphState) -> dict[str, Any]:
    return {"status": "ready_for_payment"}


def cancelled_node(state: GraphState) -> dict[str, Any]:
    return {"status": "cancelled"}


def failed_node(state: GraphState) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_message": state.get("error_message")
        or "Unable to find any results after retrying.",
    }


def needs_clarification_node(state: GraphState) -> dict[str, Any]:
    return {"status": "needs_clarification"}
