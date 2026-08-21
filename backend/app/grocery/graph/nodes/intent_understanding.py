"""Intent Understanding node.

The only node in Phase 5 backed by a real agent rather than a mock — the
Phase 4 ``IntentUnderstandingAgent`` was built and hardened (twice) for
exactly this purpose.
"""

from typing import Any, Callable

from app.grocery.agents.intent_agent import IntentUnderstandingAgent
from app.grocery.graph.state import GraphState


def make_intent_understanding_node(
    agent: IntentUnderstandingAgent,
) -> Callable[[GraphState], dict[str, Any]]:
    """Build the ``intent_understanding`` node function, closing over the
    injected agent.

    A closure (rather than a class or a module-level function reading a
    global) keeps this node's dependency explicit and swappable — tests
    inject a stub agent instead of a real LLM-backed one, the same DI
    pattern used everywhere else in this project.
    """

    def intent_understanding_node(state: GraphState) -> dict[str, Any]:
        intent = agent.extract(state["raw_text"])
        status = "needs_clarification" if intent.needs_clarification else "in_progress"
        return {"intent": intent, "status": status}

    return intent_understanding_node


def route_after_intent(state: GraphState) -> str:
    """Conditional edge: clarification-needed requests never reach
    Planning — they end the graph run immediately asking the user for
    more information, per the Phase 4 extraction-only policy.
    """

    intent = state["intent"]
    if intent is not None and intent.needs_clarification:
        return "needs_clarification_end"
    return "planning"
