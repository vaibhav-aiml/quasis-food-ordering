"""Tests for food ordering domain models and invariants."""

import pytest
from pydantic import ValidationError

from app.food_ordering.domain.intent import (
    CLARIFICATION_CONFIDENCE_CEILING,
    FoodItemRequest,
    FoodOrderIntent,
    MealType,
)
from app.food_ordering.domain.plan import (
    ExecutionStepType,
    OrderPlan,
    OrderStep,
)
from app.food_ordering.domain.restaurant import (
    CustomizationGroup,
    CustomizationOption,
    MenuItem,
    Restaurant,
)
from app.shared.domain.constraints import Constraints, Priority


def test_food_item_request_normalizes_name_and_portion() -> None:
    item = FoodItemRequest(
        name="  Chicken Biryani  ",
        quantity=2,
        portion_or_size="  Full  ",
        customizations=["  extra raita  "],
    )
    assert item.name == "chicken biryani"
    assert item.quantity == 2
    assert item.portion_or_size == "full"
    assert item.customizations == ["  extra raita  "]


def test_food_item_request_blank_name_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        FoodItemRequest(name="   ")


def test_food_order_intent_valid_with_items() -> None:
    intent = FoodOrderIntent(
        raw_text="Order chicken biryani from Meghana Foods",
        restaurant_name="Meghana Foods",
        items=[FoodItemRequest(name="chicken biryani", quantity=1)],
        confidence=0.95,
    )
    assert intent.restaurant_name == "Meghana Foods"
    assert len(intent.items) == 1
    assert intent.items[0].name == "chicken biryani"
    assert intent.target_app == "swiggy"
    assert not intent.needs_clarification


def test_food_order_intent_valid_with_restaurant_only() -> None:
    intent = FoodOrderIntent(
        raw_text="Book a breakfast from Cafe Coffee Day",
        restaurant_name="Cafe Coffee Day",
        meal_type=MealType.BREAKFAST,
        items=[],
        confidence=0.88,
        needs_clarification=False,
    )
    assert intent.restaurant_name == "Cafe Coffee Day"
    assert intent.meal_type == MealType.BREAKFAST
    assert intent.items == []
    assert not intent.needs_clarification


def test_food_order_intent_empty_unactionable_forces_clarification() -> None:
    with pytest.raises(ValidationError) as exc:
        FoodOrderIntent(
            raw_text="I want food",
            restaurant_name=None,
            meal_type=None,
            items=[],
            confidence=0.9,
            needs_clarification=False,
        )
    assert "needs_clarification must be True" in str(exc.value)


def test_food_order_intent_clarification_invariants() -> None:
    # 1. confidence ceiling enforced
    with pytest.raises(ValidationError) as exc:
        FoodOrderIntent(
            raw_text="something vague",
            items=[],
            confidence=0.8,  # > 0.5 ceiling
            needs_clarification=True,
            clarification_reason="Too vague",
        )
    assert f"confidence must be <= {CLARIFICATION_CONFIDENCE_CEILING}" in str(exc.value)

    # 2. clarification reason required
    with pytest.raises(ValidationError) as exc:
        FoodOrderIntent(
            raw_text="something vague",
            items=[],
            confidence=0.3,
            needs_clarification=True,
            clarification_reason=None,
        )
    assert "clarification_reason must be set" in str(exc.value)


def test_order_plan_creation_and_safety_invariant() -> None:
    step = OrderStep(
        step_id=1,
        step_type=ExecutionStepType.LAUNCH_APP,
        target_value="swiggy",
        expected_screen="home",
    )
    plan = OrderPlan(
        plan_id="plan_123",
        target_app="swiggy",
        restaurant_name="Meghana Foods",
        items=[FoodItemRequest(name="biryani", quantity=1)],
        steps=[step],
        stop_before_payment=True,
    )
    assert plan.plan_id == "plan_123"
    assert plan.stop_before_payment is True
    assert len(plan.steps) == 1


def test_restaurant_and_menu_models() -> None:
    opt = CustomizationOption(option_id="opt_1", name="Extra Raita", price_delta_inr=30.0)
    group = CustomizationGroup(
        group_id="grp_1",
        group_name="Add-ons",
        min_selection=0,
        max_selection=2,
        options=[opt],
    )
    dish = MenuItem(
        item_id="dish_1",
        name="Chicken Biryani",
        price_inr=320.0,
        is_veg=False,
        customization_groups=[group],
    )
    restaurant = Restaurant(
        restaurant_id="rest_1",
        name="Meghana Foods",
        rating=4.5,
        eta_minutes=25,
        cuisines=["Biryani", "Andhra"],
        menu=[dish],
    )

    assert restaurant.name == "Meghana Foods"
    assert restaurant.menu[0].name == "Chicken Biryani"
    assert restaurant.menu[0].customization_groups[0].options[0].name == "Extra Raita"
