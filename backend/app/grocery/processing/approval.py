"""Human Approval Flow.

Per Phase 0 architecture doc, section 4/10 and the master phase plan's
explicit instruction: user confirmation, reject flow, modify request
flow. Deterministic Python only — no LLM, no Appium (rules #1/#2/#7).

This is the real, validated version of the decision Phase 5's graph
represents as a bare string comparison in ``route_after_approval`` —
standalone and fully tested here, matching the pattern established in
Phases 7–12 (integration into the graph is Phase 15's job).
"""

from enum import Enum

from pydantic import BaseModel

from app.grocery.agents.recommendation_agent import RecommendationResult
from app.shared.domain.approval import ApprovalDecision, ApprovalSubmission
from app.shared.domain.constraints import Constraints


class ApprovalOutcomeStatus(str, Enum):
    """What should happen next, as a result of processing the human's
    decision.
    """

    PROCEED_TO_ORDER = "proceed_to_order"
    CANCELLED = "cancelled"
    RETRY_WITH_MODIFICATIONS = "retry_with_modifications"


class ApprovalOutcome(BaseModel):
    """Result of processing an ``ApprovalSubmission`` against a
    recommendation. Exactly one of ``store_id`` /
    (``updated_constraints`` or ``updated_raw_text``) is meaningfully set,
    depending on ``status``.
    """

    status: ApprovalOutcomeStatus
    store_id: str | None
    updated_constraints: Constraints | None
    updated_raw_text: str | None
    message: str


def process_approval(
    recommendation: RecommendationResult,
    submission: ApprovalSubmission,
    current_constraints: Constraints,
) -> ApprovalOutcome:
    """Apply the human's decision against the current recommendation state.

    Args:
        recommendation: Phase 12's output for the request being approved.
        submission: The human's decision, already validated by
            ``ApprovalSubmission`` itself.
        current_constraints: The ``Constraints`` currently in effect —
            needed so a partial modify (e.g. only budget changed) can
            preserve everything else the user already stated.

    Raises:
        ValueError: if the decision is ``approved`` but there is no
            viable store to approve (``recommendation.store_id is None``)
            — Phase 12 returns that state specifically to signal nothing
            was found; approving it is a caller error, not a valid outcome.
    """

    if submission.decision == ApprovalDecision.APPROVED:
        if recommendation.store_id is None:
            raise ValueError(
                "Cannot approve a recommendation with no viable store "
                "(recommendation.store_id is None)."
            )
        return ApprovalOutcome(
            status=ApprovalOutcomeStatus.PROCEED_TO_ORDER,
            store_id=recommendation.store_id,
            updated_constraints=None,
            updated_raw_text=None,
            message=f"Approved. Proceeding to order from {recommendation.store_id}.",
        )

    if submission.decision == ApprovalDecision.REJECTED:
        reason_note = (
            f" Reason: {submission.rejection_reason}"
            if submission.rejection_reason
            else ""
        )
        return ApprovalOutcome(
            status=ApprovalOutcomeStatus.CANCELLED,
            store_id=None,
            updated_constraints=None,
            updated_raw_text=None,
            message=f"Request cancelled by user.{reason_note}",
        )

    # MODIFY — ApprovalSubmission's own validator guarantees
    # modify_request is present here.
    modify = submission.modify_request
    assert modify is not None  # guaranteed by ApprovalSubmission's validator

    updated_constraints = Constraints(
        max_delivery_minutes=(
            modify.updated_max_delivery_minutes
            if modify.updated_max_delivery_minutes is not None
            else current_constraints.max_delivery_minutes
        ),
        max_budget=(
            modify.updated_max_budget
            if modify.updated_max_budget is not None
            else current_constraints.max_budget
        ),
        priority=(
            modify.updated_priority
            if modify.updated_priority is not None
            else current_constraints.priority
        ),
    )

    return ApprovalOutcome(
        status=ApprovalOutcomeStatus.RETRY_WITH_MODIFICATIONS,
        store_id=None,
        updated_constraints=updated_constraints,
        updated_raw_text=modify.updated_raw_text,
        message=(
            "Restating request; re-running intent understanding."
            if modify.updated_raw_text is not None
            else "Modifying constraints; re-running planning and ranking."
        ),
    )
