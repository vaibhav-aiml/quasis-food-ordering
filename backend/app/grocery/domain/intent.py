"""The structured representation of a user's shopping intent.

This is the output of the Intent Understanding Agent (Phase 4) and the
input to the Planning Agent (Phase 5 onward) — the contract described in
Phase 0 architecture doc, section 11.
"""

from pydantic import BaseModel, Field, model_validator

from app.shared.domain.constraints import Constraints
from app.grocery.domain.product import ProductRequest

CLARIFICATION_CONFIDENCE_CEILING: float = 0.5
"""Maximum confidence a request may carry once flagged as needing
clarification.

Enforced in two places, deliberately: here (as a domain invariant — defense
in depth against *any* construction path, not just the agent) and
proactively by ``IntentUnderstandingAgent``'s extraction policy (see the
Phase 4 bugfix log). Python owns this rule; the LLM's self-reported
confidence is never trusted on its own.
"""


class IntentRequest(BaseModel):
    """A fully structured, validated shopping request.

    ``raw_text`` is always the user's original, unmodified input — set by
    Python after LLM extraction, never produced by the LLM itself.

    ``products`` may be **empty**. This represents a request too ambiguous
    to safely extract concrete products from (e.g. "get me something for
    dinner") — an empty list is only valid when ``needs_clarification`` is
    True; see the validator below. This system extracts, it never
    invents: a vague request must surface as "I don't know what you want"
    (empty products + clarification flag), not as a best-guess product
    list.

    ``needs_clarification`` / ``clarification_reason`` are the explicit
    signal this system uses instead of ever guessing. Phase 5's LangGraph
    workflow is expected to route a request with
    ``needs_clarification=True`` to a clarification/re-prompt path rather
    than proceeding to planning — this model doesn't implement that
    routing, only exposes the signal it needs.
    """

    raw_text: str = Field(min_length=1)
    products: list[ProductRequest] = Field(
        description=(
            "Products explicitly requested by the user. Empty when the "
            "request was too ambiguous to extract any without guessing."
        )
    )
    constraints: Constraints = Field(default_factory=Constraints)
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Extraction confidence. Capped at "
            f"{CLARIFICATION_CONFIDENCE_CEILING} whenever "
            "needs_clarification is True."
        ),
    )
    needs_clarification: bool = Field(
        default=False,
        description=(
            "True when the request was too ambiguous to safely extract "
            "concrete products/constraints without guessing."
        ),
    )
    clarification_reason: str | None = Field(
        default=None,
        description=(
            "Human-readable reason clarification is needed. Required "
            "(non-null) whenever needs_clarification is True."
        ),
    )

    @model_validator(mode="after")
    def _enforce_clarification_invariants(self) -> "IntentRequest":
        """Deterministic, Python-owned consistency rules — never relies on
        the LLM (or any other caller) to have gotten this right on its own.
        """

        if not self.products and not self.needs_clarification:
            raise ValueError(
                "needs_clarification must be True when no products were "
                "extracted — an empty product list can never represent a "
                "ready-to-order request."
            )

        if self.needs_clarification:
            if self.confidence > CLARIFICATION_CONFIDENCE_CEILING:
                raise ValueError(
                    f"confidence must be <= {CLARIFICATION_CONFIDENCE_CEILING} "
                    "when needs_clarification is True"
                )
            if not self.clarification_reason:
                raise ValueError(
                    "clarification_reason must be set when "
                    "needs_clarification is True"
                )

        return self
