"""Food ordering intent domain models."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.domain.constraints import Constraints

CLARIFICATION_CONFIDENCE_CEILING: float = 0.5


class MealType(str, Enum):
    """Identified meal category if explicitly stated."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    BEVERAGE = "beverage"
    DESSERT = "dessert"


class FoodItemRequest(BaseModel):
    """A single food item or dish requested by the user."""

    name: str = Field(min_length=1, description="Dish/item name, e.g. 'chicken biryani'.")
    quantity: int = Field(default=1, gt=0, description="Number of portions/items.")
    portion_or_size: str | None = Field(
        default=None,
        description="Portion size e.g. 'half', 'full', 'regular', 'large', if stated.",
    )
    customizations: list[str] = Field(
        default_factory=list,
        description="Customization requests e.g. ['extra raita', 'less spicy', 'no onions'].",
    )
    preferred_restaurant: str | None = Field(
        default=None,
        description="Specific restaurant requested for this item, if different from top-level.",
    )

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Item name must not be blank")
        return normalized

    @field_validator("portion_or_size")
    @classmethod
    def _normalize_portion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class FoodOrderIntent(BaseModel):
    """Fully structured and validated food-ordering intent."""

    raw_text: str = Field(min_length=1, description="Original user prompt verbatim.")
    restaurant_name: str | None = Field(
        default=None,
        description="Name of restaurant if stated (e.g. 'Meghana Foods', 'Cafe Coffee Day').",
    )
    cuisine_preference: str | None = Field(
        default=None,
        description="Cuisine or food category if stated (e.g. 'North Indian', 'Biryani', 'Coffee').",
    )
    meal_type: MealType | None = Field(
        default=None,
        description="Meal classification (breakfast/lunch/dinner/snack) if explicitly mentioned.",
    )
    items: list[FoodItemRequest] = Field(
        default_factory=list,
        description="Dishes/items requested. May be empty if user only stated restaurant or meal type.",
    )
    constraints: Constraints = Field(default_factory=Constraints)
    target_app: str = Field(
        default="swiggy",
        description="Automation target app: 'swiggy' (primary) or 'zomato'.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score in the extraction. Capped when clarification is needed.",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if request lacks actionable specifics or is too ambiguous to order directly.",
    )
    clarification_reason: str | None = Field(
        default=None,
        description="Human-readable reason clarification is needed.",
    )

    @field_validator("restaurant_name")
    @classmethod
    def _normalize_restaurant(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("target_app")
    @classmethod
    def _normalize_target_app(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"swiggy", "zomato", "auto"}:
            return "swiggy"
        return normalized

    @model_validator(mode="after")
    def _enforce_clarification_invariants(self) -> "FoodOrderIntent":
        """Enforce domain invariants deterministically in Python."""
        if not self.items and not self.restaurant_name and not self.meal_type:
            if not self.needs_clarification:
                raise ValueError(
                    "needs_clarification must be True when no items, restaurant, "
                    "or meal type could be extracted."
                )

        if self.needs_clarification:
            if self.confidence > CLARIFICATION_CONFIDENCE_CEILING:
                raise ValueError(
                    f"confidence must be <= {CLARIFICATION_CONFIDENCE_CEILING} "
                    "when needs_clarification is True"
                )
            if not self.clarification_reason:
                raise ValueError(
                    "clarification_reason must be set when needs_clarification is True"
                )

        return self
