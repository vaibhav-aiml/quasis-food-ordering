"""Graph assembly — Phase 15 rewrite: every node now uses real Phases
7-14 logic, injected via dependencies rather than Phase 5's private
mocks (``app.grocery.graph.mocks``, deleted this phase).
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.grocery.adapters.base import StoreAdapter
from app.grocery.agents.intent_agent import IntentUnderstandingAgent
from app.grocery.agents.recommendation_agent import RecommendationGenerator
from app.grocery.graph.nodes.approval import awaiting_approval_node, route_after_approval
from app.grocery.graph.nodes.intent_understanding import (
    make_intent_understanding_node,
    route_after_intent,
)
from app.grocery.graph.nodes.normalization import normalization_node
from app.grocery.graph.nodes.order_execution import (
    make_order_execution_node,
    route_after_order_execution,
)
from app.grocery.graph.nodes.planning import make_planning_node
from app.grocery.graph.nodes.ranking import ranking_node
from app.grocery.graph.nodes.recommendation import (
    make_recommendation_generation_node,
    route_after_recommendation,
)
from app.grocery.graph.nodes.terminal import (
    cancelled_node,
    failed_node,
    needs_clarification_node,
    ready_for_payment_node,
)
from app.grocery.graph.nodes.tool_orchestration import (
    make_tool_orchestration_node,
    retry_orchestration_node,
    route_after_tool_orchestration,
)
from app.grocery.graph.nodes.verification import verification_node
from app.grocery.graph.state import GraphState


def build_graph(
    intent_agent: IntentUnderstandingAgent,
    adapters: list[StoreAdapter],
    recommendation_generator: RecommendationGenerator,
):
    """Build and compile the shopping workflow graph.

    Args:
        intent_agent: Phase 4's Intent Understanding Agent.
        adapters: Which ``StoreAdapter`` instances to search/order from.
            Pass Phase 7's mock adapters (``get_all_store_adapters()``)
            for deterministic testing/CI, or Phase 8/14's real
            Appium-backed adapters (``create_zepto_appium_adapter()``
            etc.) once real locators exist, for genuine device
            automation — ``StoreAdapter``'s Protocol design (Phase 7) is
            exactly what makes this a drop-in swap with zero graph
            rewiring.
        recommendation_generator: Phase 12's LLM-backed explanation agent.

    Returns a compiled LangGraph app — call ``.invoke(state, config)`` to
    run, where ``config = {"configurable": {"thread_id": <id>}}``.
    """

    adapters_by_id = {adapter.get_store_id(): adapter for adapter in adapters}

    builder = StateGraph(GraphState)

    builder.add_node("intent_understanding", make_intent_understanding_node(intent_agent))
    builder.add_node("planning", make_planning_node(adapters))
    builder.add_node("tool_orchestration", make_tool_orchestration_node(adapters_by_id))
    builder.add_node("retry_orchestration", retry_orchestration_node)
    builder.add_node("verification", verification_node)
    builder.add_node("normalization", normalization_node)
    builder.add_node("ranking", ranking_node)
    builder.add_node(
        "recommendation_generation",
        make_recommendation_generation_node(recommendation_generator),
    )
    builder.add_node("awaiting_approval", awaiting_approval_node)
    builder.add_node("order_execution", make_order_execution_node(adapters_by_id))
    builder.add_node("ready_for_payment", ready_for_payment_node)
    builder.add_node("cancelled", cancelled_node)
    builder.add_node("failed", failed_node)
    builder.add_node("needs_clarification_end", needs_clarification_node)

    builder.add_edge(START, "intent_understanding")

    builder.add_conditional_edges(
        "intent_understanding",
        route_after_intent,
        {
            "planning": "planning",
            "needs_clarification_end": "needs_clarification_end",
        },
    )

    builder.add_edge("planning", "tool_orchestration")

    builder.add_conditional_edges(
        "tool_orchestration",
        route_after_tool_orchestration,
        {
            "verification": "verification",
            "retry_orchestration": "retry_orchestration",
            "failed": "failed",
        },
    )
    builder.add_edge("retry_orchestration", "tool_orchestration")

    builder.add_edge("verification", "normalization")
    builder.add_edge("normalization", "ranking")
    builder.add_edge("ranking", "recommendation_generation")

    builder.add_conditional_edges(
        "recommendation_generation",
        route_after_recommendation,
        {
            "awaiting_approval": "awaiting_approval",
            "failed": "failed",
        },
    )

    builder.add_conditional_edges(
        "awaiting_approval",
        route_after_approval,
        {
            "order_execution": "order_execution",
            "planning": "planning",
            "intent_understanding": "intent_understanding",
            "cancelled": "cancelled",
        },
    )

    builder.add_conditional_edges(
        "order_execution",
        route_after_order_execution,
        {
            "ready_for_payment": "ready_for_payment",
            "failed": "failed",
        },
    )

    builder.add_edge("ready_for_payment", END)
    builder.add_edge("cancelled", END)
    builder.add_edge("failed", END)
    builder.add_edge("needs_clarification_end", END)

    return builder.compile(checkpointer=InMemorySaver())
