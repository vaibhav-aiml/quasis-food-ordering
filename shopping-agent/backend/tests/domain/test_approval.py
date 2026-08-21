"""Tests for app.domain.approval."""

import pytest
from pydantic import ValidationError

from app.domain.approval import ApprovalDecision, ApprovalSubmission, ModifyRequest
from app.domain.constraints import Priority


def test_modify_request_requires_at_least_one_change() -> None:
    with pytest.raises(ValidationError):
        ModifyRequest()


def test_modify_request_valid_with_single_change() -> None:
    modify = ModifyRequest(updated_max_budget=100.0)
    assert modify.updated_max_budget == 100.0


def test_modify_request_valid_with_raw_text() -> None:
    modify = ModifyRequest(updated_raw_text="actually I need milk")
    assert modify.updated_raw_text == "actually I need milk"


def test_approval_submission_approved_needs_no_modify_request() -> None:
    submission = ApprovalSubmission(decision=ApprovalDecision.APPROVED)
    assert submission.modify_request is None


def test_approval_submission_modify_requires_modify_request() -> None:
    with pytest.raises(ValidationError):
        ApprovalSubmission(decision=ApprovalDecision.MODIFY)


def test_approval_submission_modify_with_payload_is_valid() -> None:
    submission = ApprovalSubmission(
        decision=ApprovalDecision.MODIFY,
        modify_request=ModifyRequest(updated_priority=Priority.FASTEST),
    )
    assert submission.modify_request.updated_priority == Priority.FASTEST


def test_approval_submission_rejects_modify_request_on_non_modify_decision() -> None:
    with pytest.raises(ValidationError):
        ApprovalSubmission(
            decision=ApprovalDecision.APPROVED,
            modify_request=ModifyRequest(updated_max_budget=100.0),
        )


def test_approval_submission_rejected_can_have_a_reason() -> None:
    submission = ApprovalSubmission(
        decision=ApprovalDecision.REJECTED, rejection_reason="too expensive"
    )
    assert submission.rejection_reason == "too expensive"
