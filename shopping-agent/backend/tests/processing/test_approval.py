"""Tests for app.processing.approval.process_approval.

Every scenario here was also runtime-verified directly in the sandbox
that built this phase — see Phase 13 docs for the transcript.
"""

import pytest

from app.agents.recommendation_agent import RecommendationResult
from app.domain.approval import ApprovalDecision, ApprovalSubmission, ModifyRequest
from app.domain.constraints import Constraints, Priority
from app.processing.approval import ApprovalOutcomeStatus, process_approval


def _recommendation(store_id: str | None) -> RecommendationResult:
    return RecommendationResult(
        store_id=store_id, explanation="x", used_fallback=False, basket=None
    )


def _constraints(
    priority: Priority | None = None,
    max_delivery_minutes: int | None = None,
    max_budget: float | None = None,
) -> Constraints:
    return Constraints(
        priority=priority,
        max_delivery_minutes=max_delivery_minutes,
        max_budget=max_budget,
    )


# --- APPROVED -------------------------------------------------------------


def test_approved_proceeds_to_order_with_correct_store() -> None:
    submission = ApprovalSubmission(decision=ApprovalDecision.APPROVED)

    outcome = process_approval(_recommendation("zepto"), submission, _constraints())

    assert outcome.status == ApprovalOutcomeStatus.PROCEED_TO_ORDER
    assert outcome.store_id == "zepto"


def test_approving_a_recommendation_with_no_store_raises() -> None:
    submission = ApprovalSubmission(decision=ApprovalDecision.APPROVED)

    with pytest.raises(ValueError):
        process_approval(_recommendation(None), submission, _constraints())


# --- REJECTED -------------------------------------------------------------


def test_rejected_cancels_with_reason_in_message() -> None:
    submission = ApprovalSubmission(
        decision=ApprovalDecision.REJECTED, rejection_reason="too expensive"
    )

    outcome = process_approval(_recommendation("zepto"), submission, _constraints())

    assert outcome.status == ApprovalOutcomeStatus.CANCELLED
    assert "too expensive" in outcome.message


def test_rejected_without_reason_still_cancels() -> None:
    submission = ApprovalSubmission(decision=ApprovalDecision.REJECTED)

    outcome = process_approval(_recommendation("zepto"), submission, _constraints())

    assert outcome.status == ApprovalOutcomeStatus.CANCELLED
    assert outcome.message == "Request cancelled by user."


# --- MODIFY -------------------------------------------------------------


def test_modify_constraints_preserves_unspecified_current_values() -> None:
    current = _constraints(priority=Priority.CHEAPEST, max_delivery_minutes=20)
    submission = ApprovalSubmission(
        decision=ApprovalDecision.MODIFY,
        modify_request=ModifyRequest(updated_max_budget=100.0),
    )

    outcome = process_approval(_recommendation("zepto"), submission, current)

    assert outcome.status == ApprovalOutcomeStatus.RETRY_WITH_MODIFICATIONS
    assert outcome.updated_constraints.max_budget == 100.0
    assert outcome.updated_constraints.max_delivery_minutes == 20  # preserved
    assert outcome.updated_constraints.priority == Priority.CHEAPEST  # preserved
    assert outcome.updated_raw_text is None


def test_modify_constraints_overrides_only_specified_fields() -> None:
    current = _constraints(priority=Priority.CHEAPEST, max_budget=50.0)
    submission = ApprovalSubmission(
        decision=ApprovalDecision.MODIFY,
        modify_request=ModifyRequest(updated_priority=Priority.FASTEST),
    )

    outcome = process_approval(_recommendation("zepto"), submission, current)

    assert outcome.updated_constraints.priority == Priority.FASTEST
    assert outcome.updated_constraints.max_budget == 50.0  # preserved


def test_modify_raw_text_signals_full_reextraction() -> None:
    submission = ApprovalSubmission(
        decision=ApprovalDecision.MODIFY,
        modify_request=ModifyRequest(updated_raw_text="actually I need milk instead"),
    )

    outcome = process_approval(_recommendation("zepto"), submission, _constraints())

    assert outcome.updated_raw_text == "actually I need milk instead"
    assert "intent understanding" in outcome.message


def test_modify_constraints_only_message_mentions_planning_not_intent() -> None:
    submission = ApprovalSubmission(
        decision=ApprovalDecision.MODIFY,
        modify_request=ModifyRequest(updated_max_budget=100.0),
    )

    outcome = process_approval(_recommendation("zepto"), submission, _constraints())

    assert "planning" in outcome.message
    assert "intent" not in outcome.message
