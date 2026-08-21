"""Food Ordering Intent Understanding Agent.

Parses free-text food ordering requests into a structured, validated
FoodOrderIntent using the shared StructuredLLMService and a multi-layer
anti-hallucination policy.
"""

import logging
from app.core.llm.structured import StructuredLLMService
from app.food_ordering.domain.intent import (
    CLARIFICATION_CONFIDENCE_CEILING,
    FoodOrderIntent,
)
from app.food_ordering.services.intent_sanitizer import (
    ExtractedFoodIntent,
    looks_obviously_vague,
    sanitize_extracted_food_intent,
)
from app.shared.domain.constraints import Constraints

_logger = logging.getLogger("app.food_ordering.agents.intent")


class FoodIntentAgent:
    """Extracts structured food-ordering intent from natural language."""

    def __init__(self, llm: StructuredLLMService) -> None:
        self._llm = llm

    def extract(self, raw_text: str) -> FoodOrderIntent:
        """Extract and validate food-ordering intent.

        Args:
            raw_text: Raw user input text.

        Returns:
            A strictly validated FoodOrderIntent.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text must not be empty")

        # Layer 0: Pre-LLM check for vague/filler prompts
        if looks_obviously_vague(raw_text):
            _logger.info(
                "food_intent_short_circuited_vague_request",
                extra={"raw_text": raw_text},
            )
            return FoodOrderIntent(
                raw_text=raw_text,
                restaurant_name=None,
                cuisine_preference=None,
                meal_type=None,
                items=[],
                constraints=Constraints(),
                target_app="swiggy",
                confidence=0.0,
                needs_clarification=True,
                clarification_reason=(
                    "The request did not specify any specific restaurant or dish. "
                    "Please state what you would like to eat or where to order from."
                ),
            )

        # Layer 1: Schema-constrained LLM generation
        extracted = self._llm.generate(
            template_name="food_intent_extraction",
            response_model=ExtractedFoodIntent,
            variables={"user_message": raw_text},
        )

        # Layer 2: Deterministic Python post-LLM sanitization
        sanitized = sanitize_extracted_food_intent(extracted, raw_text)
        return sanitized
