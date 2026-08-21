"""A single product the user is asking to buy."""

from pydantic import BaseModel, Field, field_validator


class ProductRequest(BaseModel):
    """One product requested by the user, before any store search happens.

    ``name`` is always normalized (trimmed, lowercased) by the validator
    below — this holds true regardless of *how* a ``ProductRequest`` gets
    constructed (LLM extraction, direct API input, tests), which is why
    the normalization lives here rather than in agent-level cleanup code.
    """

    name: str = Field(min_length=1, description="Product name, e.g. 'onion'.")
    quantity: float = Field(
        default=1.0,
        gt=0,
        description="How many/much of the product. Defaults to 1 when unstated.",
    )
    unit: str = Field(
        default="unit",
        min_length=1,
        description="Unit for quantity, e.g. 'kg', 'litre', or 'unit' for count.",
    )

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("product name must not be blank")
        return normalized

    @field_validator("unit")
    @classmethod
    def _normalize_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("unit must not be blank")
        return normalized
