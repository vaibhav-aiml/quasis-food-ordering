"""Planning node — Phase 15: real store selection via injected adapters.

Replaces Phase 5's mock stand-in (``app.grocery.graph.mocks.select_mock_stores``,
now deleted). Uses whichever ``StoreAdapter`` instances ``build_graph()``
was given — Phase 7's mocks by default, or Phase 8/14's real
Appium-backed adapters once real locators exist. Store selection is just
"is this adapter currently available" (per the ``StoreAdapter`` protocol);
no product-catalog-aware reasoning yet — that's still a documented future
improvement (Phase 0 §5.1's real Planning Agent reasoning has no
dedicated phase of its own yet).
"""

from typing import Any, Sequence

from app.grocery.adapters.base import StoreAdapter
from app.grocery.graph.state import GraphState


def make_planning_node(adapters: Sequence[StoreAdapter]):
    def planning_node(state: GraphState) -> dict[str, Any]:
        intent = state["intent"]
        if intent is None or not intent.products:
            return {"selected_stores": []}

        selected: list[str] = []
        for adapter in adapters:
            # An adapter is available if it reports True, or if it is a real
            # Appium adapter configured for lazy on-demand session startup.
            is_avail = adapter.is_available() or hasattr(adapter, "_ensure_session")
            if is_avail:
                selected.append(adapter.get_store_id())

        return {"selected_stores": selected}

    return planning_node
