"""Tests for Food Ordering FastAPI endpoints."""

import json
from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import get_food_intent_agent, get_food_planner_agent
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.food_ordering.agents.food_intent_agent import FoodIntentAgent
from app.food_ordering.agents.food_planner_agent import FoodPlannerAgent
from app.food_ordering.domain.intent import FoodItemRequest, FoodOrderIntent, MealType
from app.food_ordering.services.plan_builder import FoodPlanBuilder
from app.main import create_app
from tests.food_ordering.test_food_intent_agent import FakeLLMClient


@pytest.fixture
def fake_food_intent_agent() -> FoodIntentAgent:
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
    return FoodIntentAgent(service)


@pytest.fixture
def client(fake_food_intent_agent: FoodIntentAgent) -> TestClient:
    app = create_app()
    plan_builder = FoodPlanBuilder()
    planner_agent = FoodPlannerAgent(fake_food_intent_agent, plan_builder)

    app.dependency_overrides[get_food_intent_agent] = lambda: fake_food_intent_agent
    app.dependency_overrides[get_food_planner_agent] = lambda: planner_agent

    return TestClient(app)


def test_api_parse_food_intent(client: TestClient) -> None:
    response = client.post(
        "/v1/food/intent/parse",
        json={"raw_text": "Order chicken biryani from Meghana Foods with extra raita"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["restaurant_name"] == "Meghana Foods"
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "chicken biryani"
    assert data["target_app"] == "swiggy"
    assert data["needs_clarification"] is False


def test_api_create_food_order_plan_from_text(client: TestClient) -> None:
    response = client.post(
        "/v1/food/order/plan",
        json={"raw_text": "Order chicken biryani from Meghana Foods with extra raita"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["ready_to_automate"] is True
    assert data["plan"] is not None
    assert data["plan"]["restaurant_name"] == "Meghana Foods"
    assert data["plan"]["stop_before_payment"] is True
    assert len(data["plan"]["steps"]) > 0


def test_api_create_food_order_plan_from_intent(client: TestClient) -> None:
    intent = FoodOrderIntent(
        raw_text="Book a breakfast from Cafe Coffee Day",
        restaurant_name="Cafe Coffee Day",
        meal_type=MealType.BREAKFAST,
        items=[],
        target_app="swiggy",
        confidence=0.9,
    )
    response = client.post(
        "/v1/food/order/plan",
        json={"intent": intent.model_dump(mode="json")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["ready_to_automate"] is True
    assert data["plan"] is not None
    assert data["plan"]["restaurant_name"] == "Cafe Coffee Day"


def test_api_create_food_order_plan_missing_payload_returns_400(client: TestClient) -> None:
    response = client.post("/v1/food/order/plan", json={})
    assert response.status_code == 400
    assert "Either 'raw_text' or 'intent' must be provided" in response.json()["detail"]
