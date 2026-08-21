"""Normalized product — the common schema every store's raw results are
mapped into.

Per Phase 0 architecture doc, section 11: the contract Ranking
(Phase 11), Recommendation Generation (Phase 12), and Order Execution
(Phase 14) all consume, regardless of which store or which raw scraping
format produced the underlying data. Unlike ``RawProductResult``, every
field here is fully typed and validated — by the time something is a
``NormalizedProduct``, it's safe for downstream numeric comparison
(ranking by price, filtering by ETA) without any further parsing.
"""

from pydantic import BaseModel, Field


class NormalizedProduct(BaseModel):
    """One product, from one store, in the system's common schema."""

    store_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    price_inr: float = Field(gt=0)
    eta_minutes: int = Field(gt=0)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)
    in_stock: bool = Field(
        default=True,
        description=(
            "Defaults to True — RawProductResult (Phase 0's own spec) "
            "has no explicit stock-status field, so there is currently "
            "no real signal to derive this from. See Phase 10 known "
            "limitations."
        ),
    )
