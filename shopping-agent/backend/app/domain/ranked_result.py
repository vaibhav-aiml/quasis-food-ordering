"""Ranked result — one product's ranked position among its cross-store
options.

Per Phase 0 architecture doc, section 11: wraps exactly one
``NormalizedProduct`` — this is what constrains the Ranking Engine
(Phase 11) to rank per-requested-product rather than per-basket. See
``app.processing.ranking`` module docstring for the full reasoning.
"""

from pydantic import BaseModel, Field

from app.domain.normalized_product import NormalizedProduct


class RankedResult(BaseModel):
    """One product's rank among its options for a single requested item."""

    product: NormalizedProduct
    rank: int = Field(ge=1)
    score: float
    rationale: str | None = Field(
        default=None,
        description=(
            "Short, deterministic, templated note — NOT LLM-generated. "
            "Only set for the top-ranked (rank=1) result."
        ),
    )
