"""Delivery/budget/priority constraints extracted from a user's request."""

from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """How the Ranking Engine (Phase 11) should weigh candidate results.

    Str-based Enum so it serializes as a plain string in JSON — both when
    the LLM produces it and when the API returns it — without needing a
    custom encoder anywhere.
    """

    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST_VALUE = "best_value"


class Constraints(BaseModel):
    """User-stated constraints on the shopping request.

    All three fields are optional, ``priority`` included. A missing
    ``priority`` means the user genuinely expressed no preference — it is
    NOT defaulted to ``BEST_VALUE`` here. Applying a default when the
    user stated no preference is the Ranking Engine's job (Phase 11), a
    deterministic decision made at ranking time, not something baked into
    the extracted data itself. Collapsing "unstated" and "explicitly
    wants balance" into the same value would be exactly the kind of
    information loss the Phase 4 extraction-only policy exists to avoid.
    """

    max_delivery_minutes: int | None = Field(
        default=None,
        ge=1,
        description="Maximum acceptable delivery time in minutes, if stated.",
    )
    priority: Priority | None = Field(
        default=None,
        description=(
            "Ranking priority the user explicitly expressed, or None if "
            "they stated no preference. Defaulting (e.g. to best_value) "
            "happens downstream in the Ranking Engine, not here."
        ),
    )
    max_budget: float | None = Field(
        default=None,
        gt=0,
        description="Maximum total budget in INR, if stated.",
    )
