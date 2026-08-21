"""Tests for Food Ordering Intent Understanding Agent."""

import json
from typing import Any
import pytest

from app.core.llm.client import LLMClient
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.food_ordering.agents.food_intent_agent import FoodIntentAgent
from app.food_ordering.domain.intent import MealType
from app.shared.domain.constraints import Priority


class FakeLLMClient:
    """Deterministic fake LLM client for testing."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self.recorded_calls: list[dict[str, Any]] = []

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.recorded_calls.append({"messages": messages, "response_format": response_format})
        if self._responses:
            return self._responses.pop(0)
        raise RuntimeError("No fake responses remaining in FakeLLMClient")


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def structured_service(fake_llm: FakeLLMClient) -> StructuredLLMService:
    return StructuredLLMService(fake_llm, PromptManager())


@pytest.fixture
def agent(structured_service: StructuredLLMService) -> FoodIntentAgent:
    return FoodIntentAgent(structured_service)


def test_empty_raw_text_raises_value_error(agent: FoodIntentAgent) -> None:
    with pytest.raises(ValueError):
        agent.extract("")


def test_vague_request_short_circuits_without_calling_llm(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    vague_texts = [
        "get me something for dinner",
        "I need food",
        "buy some snack",
        "order something",
    ]
    for text in vague_texts:
        intent = agent.extract(text)
        assert intent.needs_clarification is True
        assert intent.confidence == 0.0
        assert intent.items == []
        assert intent.clarification_reason is not None
        assert len(fake_llm.recorded_calls) == 0  # Pre-LLM short circuit


def test_extract_dish_restaurant_and_customization(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    raw = "Order 1 chicken biryani from Meghana Foods with extra raita under 30 mins"
    fake_response = json.dumps(
        {
            "restaurant_name": "Meghana Foods",
            "cuisine_preference": "Biryani",
            "meal_type": "dinner",
            "items": [
                {
                    "name": "chicken biryani",
                    "quantity": 1,
                    "portion_or_size": "",
                    "customizations": ["extra raita"],
                    "preferred_restaurant": "Meghana Foods",
                }
            ],
            "constraints": {
                "max_delivery_minutes": 30,
                "priority": "fastest",
                "max_budget": 0.0,
            },
            "target_app": "swiggy",
            "confidence": 0.95,
            "needs_clarification": False,
            "clarification_reason": "",
        }
    )
    fake_llm._responses.append(fake_response)

    intent = agent.extract(raw)

    assert intent.restaurant_name == "Meghana Foods"
    assert len(intent.items) == 1
    assert intent.items[0].name == "chicken biryani"
    assert intent.items[0].quantity == 1
    assert intent.items[0].customizations == ["extra raita"]
    assert intent.constraints.max_delivery_minutes == 30
    assert intent.constraints.priority == Priority.FASTEST
    assert not intent.needs_clarification
    assert intent.confidence == 0.95


def test_extract_cafe_coffee_day_breakfast(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    raw = "Book a breakfast from Cafe Coffee Day"
    fake_response = json.dumps(
        {
            "restaurant_name": "Cafe Coffee Day",
            "cuisine_preference": "Cafe",
            "meal_type": "breakfast",
            "items": [],
            "constraints": {
                "max_delivery_minutes": 0,
                "priority": "unspecified",
                "max_budget": 0.0,
            },
            "target_app": "swiggy",
            "confidence": 0.9,
            "needs_clarification": False,
            "clarification_reason": "",
        }
    )
    fake_llm._responses.append(fake_response)

    intent = agent.extract(raw)

    assert intent.restaurant_name == "Cafe Coffee Day"
    assert intent.meal_type == MealType.BREAKFAST
    assert intent.items == []
    assert not intent.needs_clarification
    assert intent.target_app == "swiggy"


def test_rejects_hallucinated_dishes_not_in_raw_text(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    raw = "Order from Meghana Foods"
    # LLM hallucinates chicken biryani and butter naan which were not stated
    fake_response = json.dumps(
        {
            "restaurant_name": "Meghana Foods",
            "cuisine_preference": "",
            "meal_type": "",
            "items": [
                {"name": "chicken biryani", "quantity": 1, "portion_or_size": "", "customizations": [], "preferred_restaurant": ""},
                {"name": "butter naan", "quantity": 2, "portion_or_size": "", "customizations": [], "preferred_restaurant": ""},
            ],
            "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0.0},
            "target_app": "swiggy",
            "confidence": 0.9,
            "needs_clarification": False,
            "clarification_reason": "",
        }
    )
    fake_llm._responses.append(fake_response)

    intent = agent.extract(raw)

    # Sanitizer drops hallucinated dishes
    assert intent.items == []
    assert intent.restaurant_name == "Meghana Foods"
    # Clarification flag set because hallucinated dishes were dropped
    assert intent.needs_clarification is True
    assert "Excluded unmentioned dish(es)" in (intent.clarification_reason or "")


def test_sanitizes_quantities_and_constraints_when_no_digits(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    raw = "I want paneer butter masala from Empire Restaurant"  # No numbers in input
    fake_response = json.dumps(
        {
            "restaurant_name": "Empire Restaurant",
            "cuisine_preference": "",
            "meal_type": "",
            "items": [
                {"name": "paneer butter masala", "quantity": 5, "portion_or_size": "", "customizations": [], "preferred_restaurant": ""}
            ],
            "constraints": {"max_delivery_minutes": 30, "priority": "cheapest", "max_budget": 500.0},
            "target_app": "swiggy",
            "confidence": 0.9,
            "needs_clarification": False,
            "clarification_reason": "",
        }
    )
    fake_llm._responses.append(fake_response)

    intent = agent.extract(raw)

    assert intent.items[0].name == "paneer butter masala"
    assert intent.items[0].quantity == 1  # Reset to 1 because no digits in raw text
    assert intent.constraints.max_delivery_minutes is None  # Reset because no digits
    assert intent.constraints.max_budget is None  # Reset because no digits
    assert intent.constraints.priority == Priority.CHEAPEST  # Non-numeric priority preserved


def test_zomato_target_app_detection(
    agent: FoodIntentAgent, fake_llm: FakeLLMClient
) -> None:
    raw = "Order burger from McDonald's on Zomato"
    fake_response = json.dumps(
        {
            "restaurant_name": "McDonald's",
            "cuisine_preference": "Burger",
            "meal_type": "",
            "items": [
                {"name": "burger", "quantity": 1, "portion_or_size": "", "customizations": [], "preferred_restaurant": ""}
            ],
            "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0.0},
            "target_app": "zomato",
            "confidence": 0.95,
            "needs_clarification": False,
            "clarification_reason": "",
        }
    )
    fake_llm._responses.append(fake_response)

    intent = agent.extract(raw)
    assert intent.target_app == "zomato"
