"""Awaiting Approval node — Phase 15: real Human Approval Flow (Phase 13).

Pause/resume mechanism unchanged from Phase 5 (``interrupt()``/
``Command(resume=...)``). What changed: the resumed value is now parsed
into a real ``ApprovalSubmission`` and processed via ``process_approval()``
— and routing now supports a genuine cycle back to
``intent_understanding``, not just ``planning``, when the user restates
their whole request (Phase 13's ``updated_raw_text`` signal, finally
consumed here).
"""

from typing import Any

from langgraph.types import interrupt

from app.shared.domain.approval import ApprovalSubmission
from app.shared.domain.constraints import Constraints
from app.grocery.graph.state import GraphState
from app.grocery.processing.approval import ApprovalOutcomeStatus, process_approval


def awaiting_approval_node(state: GraphState) -> dict[str, Any]:
    recommendation = state["recommendation"]

    resumed_value = interrupt(
        {
            "recommendation": recommendation.explanation if recommendation else None,
            "store_id": recommendation.store_id if recommendation else None,
            "message": (
                "Submit an approval decision as a dict matching "
                "ApprovalSubmission, e.g. {'decision': 'approved'}, "
                "{'decision': 'rejected', 'rejection_reason': '...'}, or "
                "{'decision': 'modify', 'modify_request': {...}}."
            ),
        }
    )

    submission = ApprovalSubmission.model_validate(resumed_value)
    intent = state["intent"]
    current_constraints = intent.constraints if intent else Constraints()

    outcome = process_approval(recommendation, submission, current_constraints)

    updates: dict[str, Any] = {"approval_outcome": outcome}

    if outcome.status == ApprovalOutcomeStatus.RETRY_WITH_MODIFICATIONS:
        if outcome.updated_raw_text is not None:
            # Full restatement — re-run intent understanding on the new text.
            updates["raw_text"] = outcome.updated_raw_text
        elif outcome.updated_constraints is not None and intent is not None:
            # Constraints-only tweak — thread the new constraints into the
            # existing intent so re-planning/re-ranking picks them up
            # without re-extracting anything.
            updates["intent"] = intent.model_copy(
                update={"constraints": outcome.updated_constraints}
            )

    return updates


def route_after_approval(state: GraphState) -> str:
    outcome = state["approval_outcome"]
    if outcome is None:
        return "cancelled"
    if outcome.status == ApprovalOutcomeStatus.PROCEED_TO_ORDER:
        return "order_execution"
    if outcome.status == ApprovalOutcomeStatus.RETRY_WITH_MODIFICATIONS:
        if outcome.updated_raw_text is not None:
            return "intent_understanding"
        return "planning"
    return "cancelled"
