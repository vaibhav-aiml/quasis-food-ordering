"""Approval decision domain contracts.

Per Phase 0 architecture doc, section 4 (the ``AwaitingApproval`` graph
node) and section 10 (API contracts:
``POST /v1/requests/{id}/approve|reject|modify``). These are the richly
typed, self-validating versions of what Phase 5's graph currently
represents as a bare string (``state["approval_decision"]``) — this
module is the real domain layer that sits underneath that stub.
"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.domain.constraints import Priority


class ApprovalDecision(str, Enum):
    """The three outcomes a human can choose for a recommendation."""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFY = "modify"


class ModifyRequest(BaseModel):
    """What the user wants changed, when ``decision == MODIFY``.

    ``updated_raw_text`` is deliberately distinct from the constraint
    fields: setting it signals the user wants to restate their request
    entirely (needs to go back through Intent Understanding, Phase 4),
    whereas setting only constraint fields signals a smaller tweak
    (re-plan/re-rank with adjusted constraints, no re-extraction needed).
    """

    updated_raw_text: str | None = Field(
        default=None,
        description="Set only if the user wants to restate their request entirely.",
    )
    updated_max_delivery_minutes: int | None = Field(default=None, ge=1)
    updated_max_budget: float | None = Field(default=None, gt=0)
    updated_priority: Priority | None = None

    @model_validator(mode="after")
    def _require_at_least_one_change(self) -> "ModifyRequest":
        if all(
            value is None
            for value in (
                self.updated_raw_text,
                self.updated_max_delivery_minutes,
                self.updated_max_budget,
                self.updated_priority,
            )
        ):
            raise ValueError("A modify request must specify at least one change.")
        return self


class ApprovalSubmission(BaseModel):
    """What the human sends back — the decision plus any supporting data.

    Self-validates that the payload matches the decision: a ``modify``
    decision requires ``modify_request``; any other decision must not
    carry one. This is the same "deterministic Python enforces
    consistency" principle already used for ``IntentRequest``'s
    clarification invariants (Phase 4).
    """

    decision: ApprovalDecision
    rejection_reason: str | None = None
    modify_request: ModifyRequest | None = None

    @model_validator(mode="after")
    def _validate_payload_matches_decision(self) -> "ApprovalSubmission":
        if self.decision == ApprovalDecision.MODIFY and self.modify_request is None:
            raise ValueError("decision='modify' requires a modify_request payload.")
        if self.decision != ApprovalDecision.MODIFY and self.modify_request is not None:
            raise ValueError("modify_request is only valid when decision='modify'.")
        return self
