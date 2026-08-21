"""Tool Orchestration + Retry nodes — Phase 15: real store search via
injected adapters.

Replaces Phase 5's mock stand-in (``app.grocery.graph.mocks.search_mock_store``,
now deleted). A single adapter's ``AutomationError`` (or any exception)
doesn't abort the whole search — per Phase 0 architecture doc, section
12 ("partial store failure... proceed with partial results"), a failed
store is logged and skipped, and every other store's results still flow
through the pipeline.
"""

import logging
from typing import Any, Mapping

from app.grocery.adapters.base import StoreAdapter
from app.grocery.adapters.types import SearchQuery
from app.grocery.graph.state import GraphState

_logger = logging.getLogger("app.grocery.graph.tool_orchestration")

MAX_RETRIES = 2


def make_tool_orchestration_node(adapters_by_id: Mapping[str, StoreAdapter]):
    def tool_orchestration_node(state: GraphState) -> dict[str, Any]:
        intent = state["intent"]
        if intent is None or not intent.products:
            return {"raw_results": []}

        query = SearchQuery(products=intent.products)
        raw_results = []

        for store_id in state["selected_stores"]:
            adapter = adapters_by_id.get(store_id)
            if adapter is None:
                continue
            try:
                raw_results.extend(adapter.search(query))
            except Exception:
                _logger.warning(
                    "store_search_failed", extra={"store_id": store_id}
                )
                continue  # partial failure — other stores still contribute

        return {"raw_results": raw_results}

    return tool_orchestration_node


def route_after_tool_orchestration(state: GraphState) -> str:
    """Success → verification; no results with retries left →
    retry_orchestration; retries exhausted → failed.
    """

    if state["raw_results"]:
        return "verification"
    if state["retry_count"] < MAX_RETRIES:
        return "retry_orchestration"
    return "failed"


def retry_orchestration_node(state: GraphState) -> dict[str, Any]:
    return {"retry_count": state["retry_count"] + 1}
