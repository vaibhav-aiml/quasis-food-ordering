"""LangGraph state schema — Phase 15 rewrite.

Every field now holds REAL domain/processing types built across Phases
7-14, replacing Phase 5's ``MockProductResult`` placeholder entirely.
This is exactly the "replaced wholesale once real store catalogs exist"
moment Phase 5's own (now-deleted) ``mocks.py`` docstring anticipated.
"""

from typing import Literal, TypedDict

from app.grocery.adapters.types import CartActionResult, CheckoutState
from app.grocery.agents.recommendation_agent import RecommendationResult
from app.grocery.domain.intent import IntentRequest
from app.grocery.domain.normalized_product import NormalizedProduct
from app.grocery.domain.raw_product_result import RawProductResult
from app.grocery.processing.approval import ApprovalOutcome
from app.grocery.processing.ranking import RankingSummary
from app.grocery.processing.recommendation_selection import StoreBasketSummary
from app.grocery.processing.verification import VerificationResult

GraphStatus = Literal[
    "in_progress",
    "needs_clarification",
    "ready_for_payment",
    "cancelled",
    "failed",
]
"""``"ready_for_payment"`` (deliberately NOT ``"confirmed"``) is the
successful terminal status. Renamed in Phase 15 specifically because
"confirmed" reads dangerously close to "payment was confirmed" right next
to Phase 14's explicit, twice-repeated safety rule — never automatically
confirm payment. This status means the automation verified it CAN place
the order (reached the payment screen), never that it did.
"""


class GraphState(TypedDict):
    """The full state threaded through every node in the shopping workflow.

    Field-by-field ownership (which node sets it):

    - ``raw_text``: set initially by the caller; re-set by
      ``awaiting_approval`` on a full-restatement modify.
    - ``intent``: set by ``intent_understanding``; its ``constraints``
      may be replaced by ``awaiting_approval`` on a constraints-only modify.
    - ``selected_stores``: set by ``planning``.
    - ``raw_results``: set by ``tool_orchestration``.
    - ``verification_result``: set by ``verification`` (Phase 9).
    - ``normalized_products``: set by ``normalization`` (Phase 10).
    - ``ranking_summary``: set by ``ranking`` (Phase 11).
    - ``basket`` / ``recommendation``: set by ``recommendation_generation``
      (Phase 12's basket selection + LLM explanation).
    - ``selected_indices``: optional, caller-supplied (Phase 16 FastAPI
      integration). Maps a requested product name to which ranked
      candidate index to use instead of the default top rank (index 0).
      Read by ``recommendation_generation`` every time it runs — set it
      up front (initial request) or update it via
      ``POST /v1/requests/{id}/selection`` while paused at
      ``awaiting_approval`` (the API layer uses ``update_state`` there,
      which is picked up because the node re-reads state on resume).
    - ``approval_outcome``: set by ``awaiting_approval`` (Phase 13).
    - ``cart_results`` / ``checkout_state`` / ``order_confirmation``: set
      by ``order_execution`` (Phase 14).
    - ``status`` / ``error_message``: updated by whichever node reaches
      a terminal-ish state.
    - ``retry_count``: incremented by ``retry_orchestration``.
    """

    raw_text: str
    intent: IntentRequest | None
    selected_stores: list[str]
    raw_results: list[RawProductResult]
    verification_result: VerificationResult | None
    normalized_products: list[NormalizedProduct]
    ranking_summary: RankingSummary | None
    selected_indices: dict[str, int] | None
    basket: StoreBasketSummary | None
    recommendation: RecommendationResult | None
    approval_outcome: ApprovalOutcome | None
    cart_results: list[CartActionResult]
    checkout_state: CheckoutState | None
    order_confirmation: dict[str, str] | None
    status: GraphStatus
    error_message: str | None
    retry_count: int


def initial_state(raw_text: str) -> GraphState:
    """Build the starting state for a new graph run."""

    return GraphState(
        raw_text=raw_text,
        intent=None,
        selected_stores=[],
        raw_results=[],
        verification_result=None,
        normalized_products=[],
        ranking_summary=None,
        selected_indices=None,
        basket=None,
        recommendation=None,
        approval_outcome=None,
        cart_results=[],
        checkout_state=None,
        order_confirmation=None,
        status="in_progress",
        error_message=None,
        retry_count=0,
    )
