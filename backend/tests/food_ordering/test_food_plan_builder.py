"""Tests for Food Ordering Plan Builder & Planner Agent."""

import json
import pytest

from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.food_ordering.agents.food_intent_agent import FoodIntentAgent
from app.food_ordering.agents.food_planner_agent import FoodPlannerAgent
from app.food_ordering.domain.intent import FoodItemRequest, FoodOrderIntent, MealType
from app.food_ordering.domain.plan import ExecutionStepType
from app.food_ordering.services.plan_builder import FoodPlanBuilder
from tests.food_ordering.test_food_intent_agent import FakeLLMClient


def test_build_plan_full_flow_with_customization() -> None:
    intent = FoodOrderIntent(
        raw_text="Order chicken biryani from Meghana Foods with extra raita",
        restaurant_name="Meghana Foods",
        items=[
            FoodItemRequest(
                name="chicken biryani",
                quantity=1,
                portion_or_size="full",
                customizations=["extra raita"],
            )
        ],
        target_app="swiggy",
        confidence=0.95,
    )

    builder = FoodPlanBuilder()
    plan = builder.build_plan(intent)

    assert plan.target_app == "swiggy"
    assert plan.restaurant_name == "Meghana Foods"
    assert plan.stop_before_payment is True

    step_types = [s.step_type for s in plan.steps]
    expected_types = [
        ExecutionStepType.LAUNCH_APP,
        ExecutionStepType.SEARCH_RESTAURANT,
        ExecutionStepType.SELECT_RESTAURANT,
        ExecutionStepType.SEARCH_MENU_ITEM,
        ExecutionStepType.SELECT_ITEM,
        ExecutionStepType.APPLY_CUSTOMIZATION,
        ExecutionStepType.ADD_TO_CART,
        ExecutionStepType.VIEW_CART,
        ExecutionStepType.PROCEED_TO_CHECKOUT,
        ExecutionStepType.STOP_FOR_PAYMENT,
    ]
    assert step_types == expected_types

    # Verify parameters for critical steps
    customization_step = plan.steps[5]
    assert customization_step.step_type == ExecutionStepType.APPLY_CUSTOMIZATION
    assert customization_step.parameters["portion"] == "full"
    assert customization_step.parameters["customizations"] == ["extra raita"]

    payment_step = plan.steps[-1]
    assert payment_step.step_type == ExecutionStepType.STOP_FOR_PAYMENT
    assert payment_step.parameters["safety_enforced"] is True


def test_build_plan_multiple_dishes() -> None:
    intent = FoodOrderIntent(
        raw_text="2 garlic naan and 1 butter chicken from Empire Restaurant",
        restaurant_name="Empire Restaurant",
        items=[
            FoodItemRequest(name="garlic naan", quantity=2),
            FoodItemRequest(name="butter chicken", quantity=1),
        ],
        target_app="swiggy",
        confidence=0.92,
    )

    builder = FoodPlanBuilder()
    plan = builder.build_plan(intent)

    step_types = [s.step_type for s in plan.steps]

    # Should contain items sequence for both dishes
    assert step_types.count(ExecutionStepType.SEARCH_MENU_ITEM) == 2
    assert step_types.count(ExecutionStepType.SELECT_ITEM) == 2
    assert step_types.count(ExecutionStepType.ADD_TO_CART) == 2
    assert step_types[-1] == ExecutionStepType.STOP_FOR_PAYMENT


def test_build_plan_restaurant_only_browse_mode() -> None:
    intent = FoodOrderIntent(
        raw_text="Book a breakfast from Cafe Coffee Day",
        restaurant_name="Cafe Coffee Day",
        meal_type=MealType.BREAKFAST,
        items=[],
        target_app="swiggy",
        confidence=0.9,
    )

    builder = FoodPlanBuilder()
    plan = builder.build_plan(intent)

    step_types = [s.step_type for s in plan.steps]
    expected_types = [
        ExecutionStepType.LAUNCH_APP,
        ExecutionStepType.SEARCH_RESTAURANT,
        ExecutionStepType.SELECT_RESTAURANT,
    ]
    assert step_types == expected_types


def test_food_planner_agent_end_to_end() -> None:
    fake_llm = FakeLLMClient(
        [
            json.dumps(
                {
                    "restaurant_name": "Meghana Foods",
                    "cuisine_preference": "Biryani",
                    "meal_type": "",
                    "items": [
                        {
                            "name": "chicken biryani",
                            "quantity": 1,
                            "portion_or_size": "",
                            "customizations": ["extra raita"],
                            "preferred_restaurant": "Meghana Foods",
                        }
                    ],
                    "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0.0},
                    "target_app": "swiggy",
                    "confidence": 0.95,
                    "needs_clarification": False,
                    "clarification_reason": "",
                }
            )
        ]
    )
    service = StructuredLLMService(fake_llm, PromptManager())
    intent_agent = FoodIntentAgent(service)
    plan_builder = FoodPlanBuilder()
    planner = FoodPlannerAgent(intent_agent, plan_builder)

    result = planner.plan_from_text("Order chicken biryani from Meghana Foods with extra raita")

    assert result.ready_to_automate is True
    assert result.plan is not None
    assert result.plan.restaurant_name == "Meghana Foods"
    assert result.plan.stop_before_payment is True


def test_food_planner_agent_returns_unready_on_clarification() -> None:
    fake_llm = FakeLLMClient([])
    service = StructuredLLMService(fake_llm, PromptManager())
    intent_agent = FoodIntentAgent(service)
    plan_builder = FoodPlanBuilder()
    planner = FoodPlannerAgent(intent_agent, plan_builder)

    result = planner.plan_from_text("get me something for dinner")

    assert result.ready_to_automate is False
    assert result.plan is None
    assert "No specific" in result.status_message or "specific restaurant or dish" in result.status_message
