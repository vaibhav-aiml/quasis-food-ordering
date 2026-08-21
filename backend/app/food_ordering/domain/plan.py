"""Order execution plan domain models.

Defines the discrete, sequential automation steps transmitted to the
Kotlin Android AccessibilityService.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.food_ordering.domain.intent import FoodItemRequest


class ExecutionStepType(str, Enum):
    """Types of automated UI actions the Android AccessibilityService executes."""

    LAUNCH_APP = "LAUNCH_APP"
    SEARCH_RESTAURANT = "SEARCH_RESTAURANT"
    SELECT_RESTAURANT = "SELECT_RESTAURANT"
    SEARCH_MENU_ITEM = "SEARCH_MENU_ITEM"
    SELECT_ITEM = "SELECT_ITEM"
    APPLY_CUSTOMIZATION = "APPLY_CUSTOMIZATION"
    ADD_TO_CART = "ADD_TO_CART"
    VIEW_CART = "VIEW_CART"
    PROCEED_TO_CHECKOUT = "PROCEED_TO_CHECKOUT"
    STOP_FOR_PAYMENT = "STOP_FOR_PAYMENT"


class OrderStep(BaseModel):
    """One atomic step in an automated food ordering flow."""

    step_id: int = Field(ge=1, description="1-indexed sequence number.")
    step_type: ExecutionStepType
    target_value: str | None = Field(
        default=None,
        description="Primary string target (e.g. restaurant query, dish name).",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra parameters (e.g. quantity, customization options, portion).",
    )
    expected_screen: str = Field(
        description="Screen state expected when executing this step (e.g. 'home', 'restaurant_menu', 'cart').",
    )
    timeout_seconds: int = Field(
        default=15,
        ge=1,
        description="Max wait time for target UI element/screen before flagging failure.",
    )
    is_critical: bool = Field(
        default=True,
        description="If True, failure of this step aborts the plan.",
    )


class OrderPlan(BaseModel):
    """Complete, validated execution plan ready for Android automation."""

    plan_id: str = Field(min_length=1)
    target_app: str = Field(default="swiggy")
    restaurant_name: str | None = None
    items: list[FoodItemRequest] = Field(default_factory=list)
    steps: list[OrderStep] = Field(default_factory=list)
    stop_before_payment: bool = Field(
        default=True,
        description="Safety invariant: execution must stop and hand control to human before payment.",
    )
