"""``/v1/requests`` endpoints — Phase 16: FastAPI integration on top of
the Phase 15 LangGraph workflow (``app.grocery.graph.workflow.build_graph``).

This module is deliberately thin. Every real decision — intent
extraction, planning, ranking, basket selection, approval semantics,
order execution — already lives in the graph and the processing/domain
layers built across Phases 4-15. This router's only job is to:

1. Create a ``thread_id`` and kick off a graph run (``POST /``).
2. Read back the current checkpointed state for a thread (``GET /{id}``).
3. Resume a paused thread with an explicit, human-supplied approval
   decision, via LangGraph's ``Command(resume=...)`` mechanism
   (``POST /{id}/approval``) — reusing ``app.shared.domain.approval.
   ApprovalSubmission`` directly as the request body, so validation
   ("modify requires modify_request", etc.) is enforced exactly once,
   in the domain layer, not re-implemented here.
4. Let the caller pick a specific ranked candidate for a product before
   approving, by recomputing the basket/recommendation with
   ``app.grocery.processing.recommendation_selection.select_best_store`` and
   writing it back into the paused checkpoint via ``graph.update_state``
   (``POST /{id}/selection``).

No new persistence layer is introduced — the LangGraph checkpointer
(``InMemorySaver``, keyed by ``thread_id``) *is* the request store, per
Phase 0's "no database in MVP" decision and Phase 13's explicit note
that wiring real endpoints to a real request store was left for this
phase.

Safety invariants enforced here (never delegated to the frontend):
- Nothing is ever auto-approved. ``POST /`` and ``POST /selection`` never
  submit an approval decision on the caller's behalf; only
  ``POST /{id}/approval`` can, and only with an explicit, validated
  ``ApprovalSubmission`` body.
- ``ready_for_payment`` is only ever reported ``True`` when
  ``checkout_state.status == "ready_for_payment"`` in the checkpointed
  state — not merely because the graph's terminal ``status`` field says
  so (see ``route_after_order_execution`` in
  ``app.grocery.graph.nodes.order_execution`` for the matching graph-side fix
  that makes this trustworthy).
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.grocery.agents.recommendation_agent import RecommendationGenerator, RecommendationResult
from app.core.dependencies import get_recommendation_generator, get_shopping_graph_dependency
from app.shared.domain.approval import ApprovalSubmission
from app.grocery.domain.intent import IntentRequest
from app.grocery.domain.ranked_result import RankedResult
from app.grocery.graph.state import initial_state
from app.grocery.processing.recommendation_selection import select_best_store

router = APIRouter(prefix="/requests", tags=["requests"])


# --------------------------------------------------------------------------
# Request/response schemas
# --------------------------------------------------------------------------


class RequestCreate(BaseModel):
    """Body for ``POST /v1/requests``."""

    raw_text: str = Field(min_length=1, description="The user's shopping request, verbatim.")
    selected_indices: dict[str, int] | None = Field(
        default=None,
        description=(
            "Optional up-front candidate selection: maps a requested "
            "product name to which of its recommended store's own "
            "ranked candidates to use (e.g. when that store has more "
            "than one matching listing for the product), instead of the "
            "default top rank (index 0). This picks a variant WITHIN "
            "whichever store the basket-selection policy ends up "
            "recommending — it does not itself choose which store wins; "
            "see app.grocery.processing.recommendation_selection.select_best_store. "
            "Same effect as calling POST /{thread_id}/selection once the "
            "thread pauses for approval, just supplied before the run starts."
        ),
    )


class SelectionRequest(BaseModel):
    """Body for ``POST /v1/requests/{thread_id}/selection``."""

    selected_indices: dict[str, int] = Field(
        min_length=1,
        description=(
            "Maps a requested product name (as it appears in the "
            "response's `candidates` map) to the index of the ranked "
            "candidate to use for that product, WITHIN whichever store "
            "the basket-selection policy recommends for the whole "
            "order — this chooses a specific listing at that store when "
            "it has more than one, it does not pick which store wins. "
            "Every key must be a real candidate map key and every index "
            "must be within that product's candidate list; this endpoint "
            "never silently substitutes or picks multiple products on "
            "the caller's behalf."
        ),
    )


class RequestStatusResponse(BaseModel):
    """Shared response shape for create/get/approval/selection — the
    current, fully-derived view of one thread's checkpointed state.
    """

    thread_id: str
    status: str
    waiting_for_approval: bool = Field(
        description="True iff the graph is currently paused at awaiting_approval for this thread."
    )
    needs_clarification: bool = False
    clarification_reason: str | None = None
    intent: IntentRequest | None = None
    candidates: dict[str, list[RankedResult]] | None = Field(
        default=None,
        description="Ranked candidates per requested product name, when available.",
    )
    selected_indices: dict[str, int] | None = None
    recommendation: RecommendationResult | None = None
    ready_for_payment: bool = Field(
        description=(
            "True only when the real checkout flow actually reached the "
            "payment screen (checkout_state.status == 'ready_for_payment'), "
            "never merely because the graph's terminal status looks that way."
        )
    )
    order_confirmation: dict[str, str] | None = None
    error_message: str | None = None


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _get_snapshot_or_404(graph: Any, config: dict) -> Any:
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="No request found for this thread_id.")
    return snapshot


def _is_waiting_for_approval(snapshot: Any) -> bool:
    """True iff the graph is currently paused with ``awaiting_approval``
    as its next node to run for this thread.

    Deliberately checks ``snapshot.next`` rather than
    ``task.interrupts``: a freshly-paused thread has both set, but
    ``graph.update_state(...)`` (used by ``POST /{id}/selection`` to
    write a recomputed basket/recommendation into the still-paused
    checkpoint) clears the recorded ``Interrupt`` objects on the pending
    task as a side effect, even though ``awaiting_approval`` genuinely
    has not re-run yet and will hit its ``interrupt()`` call again the
    moment the thread is resumed. ``snapshot.next`` stays accurate
    across that write, since this graph only ever leaves anything
    pending in ``next`` when it stopped at an interrupt (a synchronous
    ``.invoke()`` otherwise always runs to a terminal node).
    """

    return "awaiting_approval" in snapshot.next


def _build_response(thread_id: str, snapshot: Any) -> RequestStatusResponse:
    values = snapshot.values
    intent: IntentRequest | None = values.get("intent")
    ranking_summary = values.get("ranking_summary")
    checkout_state = values.get("checkout_state")
    status = values.get("status", "in_progress")

    ready_for_payment = bool(
        status == "ready_for_payment"
        and checkout_state is not None
        and checkout_state.status == "ready_for_payment"
    )

    order_confirmation = values.get("order_confirmation")
    error_message = values.get("error_message")
    if (
        error_message is None
        and status == "failed"
        and order_confirmation is not None
        and order_confirmation.get("message")
    ):
        # order_execution_node's checkout-failure branch (as opposed to
        # its cart-failure branch) doesn't set error_message, so
        # failed_node's generic fallback text would otherwise mask the
        # real, more specific reason already captured in
        # order_confirmation.message (e.g. "Payment gateway timed out.").
        # Purely a response-shaping choice — the underlying graph/node
        # state is untouched.
        error_message = order_confirmation["message"]

    return RequestStatusResponse(
        thread_id=thread_id,
        status=status,
        waiting_for_approval=_is_waiting_for_approval(snapshot),
        needs_clarification=(status == "needs_clarification"),
        clarification_reason=(intent.clarification_reason if intent else None),
        intent=intent,
        candidates=(ranking_summary.rankings if ranking_summary else None),
        selected_indices=values.get("selected_indices"),
        recommendation=values.get("recommendation"),
        ready_for_payment=ready_for_payment,
        order_confirmation=order_confirmation,
        error_message=error_message,
    )


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.post("", response_model=RequestStatusResponse, status_code=201)
def create_request(
    payload: RequestCreate,
    graph: Annotated[Any, Depends(get_shopping_graph_dependency)],
) -> RequestStatusResponse:
    """Start a new shopping request: create a thread_id, run the graph
    up to its first pause (or a terminal state, e.g.
    ``needs_clarification``/``failed``), and return the current state.

    Never approves anything automatically — the graph run stops on its
    own at ``awaiting_approval``'s ``interrupt()`` call, exactly as it
    does when invoked directly (Phase 15's own tests rely on this same
    behavior).
    """

    thread_id = str(uuid.uuid4())
    config = _thread_config(thread_id)

    state = initial_state(payload.raw_text)
    if payload.selected_indices is not None:
        state["selected_indices"] = payload.selected_indices

    graph.invoke(state, config)

    snapshot = graph.get_state(config)
    return _build_response(thread_id, snapshot)


@router.get("/{thread_id}", response_model=RequestStatusResponse)
def get_request(
    thread_id: str,
    graph: Annotated[Any, Depends(get_shopping_graph_dependency)],
) -> RequestStatusResponse:
    """Retrieve the current LangGraph checkpoint/state for a thread."""

    snapshot = _get_snapshot_or_404(graph, _thread_config(thread_id))
    return _build_response(thread_id, snapshot)


@router.post("/{thread_id}/selection", response_model=RequestStatusResponse)
def select_candidate(
    thread_id: str,
    payload: SelectionRequest,
    graph: Annotated[Any, Depends(get_shopping_graph_dependency)],
    recommendation_generator: Annotated[
        RecommendationGenerator, Depends(get_recommendation_generator)
    ],
) -> RequestStatusResponse:
    """Let the frontend pick a specific ranked candidate per product
    before approving, and recompute the recommendation to match.

    Only valid while the thread is genuinely paused at
    ``awaiting_approval`` — there's no ranked candidate set to choose
    from before that point, and after approval the order has already
    been (or is being) acted on. The recomputed basket/recommendation is
    written into the checkpoint with ``graph.update_state`` so that when
    ``POST /{thread_id}/approval`` resumes the thread,
    ``awaiting_approval_node`` re-reads state from scratch and uses this
    selection — not the original default (top-rank) recommendation.
    """

    config = _thread_config(thread_id)
    snapshot = _get_snapshot_or_404(graph, config)

    if not _is_waiting_for_approval(snapshot):
        raise HTTPException(
            status_code=409,
            detail="This request is not currently awaiting approval; candidates can't be selected.",
        )

    ranking_summary = snapshot.values.get("ranking_summary")
    if ranking_summary is None:
        raise HTTPException(status_code=409, detail="No ranked candidates available for this request.")

    unknown_products = [
        name for name in payload.selected_indices if name not in ranking_summary.rankings
    ]
    if unknown_products:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown product name(s) in selected_indices: {', '.join(unknown_products)}",
        )

    out_of_range = [
        name
        for name, idx in payload.selected_indices.items()
        if not (0 <= idx < len(ranking_summary.rankings[name]))
    ]
    if out_of_range:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate index out of range for product(s): {', '.join(out_of_range)}",
        )

    basket = select_best_store(ranking_summary, payload.selected_indices)
    if basket is None:
        raise HTTPException(
            status_code=422,
            detail="This selection doesn't produce a viable store basket.",
        )

    recommendation = recommendation_generator.generate(basket, ranking_summary.priority_used)

    graph.update_state(
        config,
        {
            "selected_indices": payload.selected_indices,
            "basket": basket,
            "recommendation": recommendation,
        },
    )

    snapshot = graph.get_state(config)
    return _build_response(thread_id, snapshot)


@router.post("/{thread_id}/approval", response_model=RequestStatusResponse)
def submit_approval(
    thread_id: str,
    submission: ApprovalSubmission,
    graph: Annotated[Any, Depends(get_shopping_graph_dependency)],
) -> RequestStatusResponse:
    """Resume a paused thread with an explicit approval decision.

    ``submission`` is ``app.shared.domain.approval.ApprovalSubmission`` itself
    — FastAPI validates it as the request body, so an invalid payload
    (e.g. ``decision: "modify"`` with no ``modify_request``) is rejected
    with a 422 before this function body even runs, using the exact same
    rules ``awaiting_approval_node`` relies on. There is no default
    decision and no code path that resumes without one: approval is
    always explicit.
    """

    config = _thread_config(thread_id)
    snapshot = _get_snapshot_or_404(graph, config)

    if not _is_waiting_for_approval(snapshot):
        raise HTTPException(
            status_code=409,
            detail="This request is not currently awaiting approval.",
        )

    graph.invoke(Command(resume=submission.model_dump(mode="json")), config)

    snapshot = graph.get_state(config)
    return _build_response(thread_id, snapshot)
