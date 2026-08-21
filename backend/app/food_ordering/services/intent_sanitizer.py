"""Intent Sanitization & Anti-Hallucination Service for Food Ordering.

Implements the multi-layer extraction-only policy:
1. Pre-LLM short-circuit for generic filler requests.
2. Post-LLM verification of extracted entities against the user's raw text.
3. Constraint & quantity sanitization when no numbers appear in input.
4. Deterministic invariant enforcement (AI reasons, Python decides).
"""

import logging
import re
from enum import Enum
from pydantic import BaseModel, Field

from app.food_ordering.domain.intent import (
    CLARIFICATION_CONFIDENCE_CEILING,
    FoodItemRequest,
    FoodOrderIntent,
    MealType,
)
from app.shared.domain.constraints import Constraints, Priority

_logger = logging.getLogger("app.food_ordering.sanitizer")

DEFAULT_FOOD_CLARIFICATION_REASON = (
    "The request did not specify any restaurant or dish to order."
)

_VAGUE_FOOD_WORDS = frozenset(
    {
        "a", "an", "and", "anything", "app", "buy", "can", "cater",
        "dinner", "eat", "feed", "food", "for", "get", "hungry", "i",
        "item", "items", "lunch", "meal", "meals", "me", "my", "need",
        "of", "online", "or", "order", "ordering", "place", "please",
        "quick", "serve", "snack", "snacks", "some", "something", "stuff",
        "the", "to", "us", "want", "we", "whatever", "you",
    }
)


class ExtractedPriority(str, Enum):
    """LLM-facing priority enum."""

    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST_VALUE = "best_value"
    UNSPECIFIED = "unspecified"


_PRIORITY_MAP: dict[ExtractedPriority, Priority | None] = {
    ExtractedPriority.CHEAPEST: Priority.CHEAPEST,
    ExtractedPriority.FASTEST: Priority.FASTEST,
    ExtractedPriority.BEST_VALUE: Priority.BEST_VALUE,
    ExtractedPriority.UNSPECIFIED: None,
}


class ExtractedFoodConstraints(BaseModel):
    """LLM-facing constraints schema using non-nullable sentinel values."""

    max_delivery_minutes: int = Field(ge=0, default=0)
    priority: ExtractedPriority = Field(default=ExtractedPriority.UNSPECIFIED)
    max_budget: float = Field(ge=0.0, default=0.0)


class ExtractedFoodItem(BaseModel):
    """LLM-facing item schema."""

    name: str = Field(min_length=1)
    quantity: int = Field(ge=1, default=1)
    portion_or_size: str = Field(default="")
    customizations: list[str] = Field(default_factory=list)
    preferred_restaurant: str = Field(default="")


class ExtractedFoodIntent(BaseModel):
    """The raw schema produced by the LLM."""

    restaurant_name: str = Field(default="")
    cuisine_preference: str = Field(default="")
    meal_type: str = Field(default="")
    items: list[ExtractedFoodItem] = Field(default_factory=list)
    constraints: ExtractedFoodConstraints = Field(default_factory=ExtractedFoodConstraints)
    target_app: str = Field(default="swiggy")
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    needs_clarification: bool = Field(default=False)
    clarification_reason: str = Field(default="")


def looks_obviously_vague(raw_text: str) -> bool:
    """Pre-LLM check: returns True if request consists entirely of filler words.

    Examples: 'get me something for dinner', 'I am hungry, get food'.
    """
    words = re.findall(r"[a-zA-Z']+", raw_text.lower())
    if not words:
        return True
    return all(word in _VAGUE_FOOD_WORDS for word in words)


def _fuzzy_or_substring_present(target: str, haystack: str) -> bool:
    """Verify that a target phrase or its meaningful tokens appear in haystack."""
    target_clean = target.lower().strip()
    haystack_clean = haystack.lower()
    if target_clean in haystack_clean:
        return True
    # If multi-word, check if majority of significant tokens appear
    tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", target_clean) if len(t) > 2]
    if not tokens:
        return False
    matched = sum(1 for t in tokens if t in haystack_clean)
    return (matched / len(tokens)) >= 0.5


def _sanitize_items(
    items: list[ExtractedFoodItem], raw_text: str
) -> tuple[list[FoodItemRequest], list[str]]:
    """Filter out items hallucinated by the LLM and normalize valid ones."""
    has_digits = any(c.isdigit() for c in raw_text)
    valid_items: list[FoodItemRequest] = []
    rejected: list[str] = []

    for item in items:
        clean_name = item.name.strip().lower()
        if not clean_name:
            continue

        if not _fuzzy_or_substring_present(clean_name, raw_text):
            rejected.append(item.name)
            continue

        # If no digits anywhere in text, force quantity to 1
        qty = item.quantity if has_digits else 1

        # Check portion
        portion = item.portion_or_size.strip().lower() if item.portion_or_size else None
        if portion and not _fuzzy_or_substring_present(portion, raw_text):
            portion = None

        # Filter customizations to those actually referenced
        valid_customizations = [
            c.strip() for c in item.customizations
            if c.strip() and _fuzzy_or_substring_present(c, raw_text)
        ]

        pref_rest = item.preferred_restaurant.strip() or None
        if pref_rest and not _fuzzy_or_substring_present(pref_rest, raw_text):
            pref_rest = None

        valid_items.append(
            FoodItemRequest(
                name=clean_name,
                quantity=qty,
                portion_or_size=portion,
                customizations=valid_customizations,
                preferred_restaurant=pref_rest,
            )
        )

    return valid_items, rejected


def _sanitize_restaurant(restaurant: str, raw_text: str) -> str | None:
    """Verify restaurant name exists in user's prompt."""
    if not restaurant or not restaurant.strip():
        return None
    clean = restaurant.strip()
    if _fuzzy_or_substring_present(clean, raw_text):
        return clean
    return None


def _sanitize_meal_type(meal_type_str: str, raw_text: str) -> MealType | None:
    """Validate meal type is explicitly in user prompt."""
    if not meal_type_str or not meal_type_str.strip():
        return None
    clean = meal_type_str.strip().lower()
    for m in MealType:
        if m.value in clean or m.value in raw_text.lower():
            return m
    return None


def _sanitize_constraints(
    extracted: ExtractedFoodConstraints, raw_text: str
) -> Constraints:
    """Zero out numeric constraints if no digits exist in input."""
    has_digits = any(c.isdigit() for c in raw_text)

    delivery = (
        extracted.max_delivery_minutes
        if (has_digits and extracted.max_delivery_minutes > 0)
        else None
    )
    budget = (
        extracted.max_budget
        if (has_digits and extracted.max_budget > 0)
        else None
    )
    priority = _PRIORITY_MAP.get(extracted.priority)

    return Constraints(
        max_delivery_minutes=delivery,
        priority=priority,
        max_budget=budget,
    )


def sanitize_extracted_food_intent(
    extracted: ExtractedFoodIntent, raw_text: str
) -> FoodOrderIntent:
    """Process LLM output through deterministic anti-hallucination sanitization."""
    # 1. Restaurant
    restaurant = _sanitize_restaurant(extracted.restaurant_name, raw_text)

    # 2. Meal Type
    meal_type = _sanitize_meal_type(extracted.meal_type, raw_text)

    # 3. Cuisine
    cuisine = extracted.cuisine_preference.strip() or None
    if cuisine and not _fuzzy_or_substring_present(cuisine, raw_text):
        cuisine = None

    # 4. Items
    items, rejected = _sanitize_items(extracted.items, raw_text)

    # 5. Constraints
    constraints = _sanitize_constraints(extracted.constraints, raw_text)

    # 6. Clarification evaluation
    needs_clarification = extracted.needs_clarification
    reasons: list[str] = []
    if extracted.clarification_reason:
        reasons.append(extracted.clarification_reason)

    if rejected:
        _logger.warning(
            "food_intent_sanitizer_rejected_hallucinated_items",
            extra={"rejected": rejected, "raw_text": raw_text},
        )
        needs_clarification = True
        reasons.append(f"Excluded unmentioned dish(es): {', '.join(rejected)}.")

    # A request with neither dishes nor restaurant nor meal type is un-actionable
    if not items and not restaurant and not meal_type:
        needs_clarification = True
        reasons.append("No specific dish, meal, or restaurant identified.")

    confidence = extracted.confidence
    if needs_clarification:
        confidence = min(confidence, CLARIFICATION_CONFIDENCE_CEILING)
        final_reason = " ".join(dict.fromkeys(reasons)) or DEFAULT_FOOD_CLARIFICATION_REASON
    else:
        final_reason = None

    return FoodOrderIntent(
        raw_text=raw_text,
        restaurant_name=restaurant,
        cuisine_preference=cuisine,
        meal_type=meal_type,
        items=items,
        constraints=constraints,
        target_app=extracted.target_app or "swiggy",
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_reason=final_reason,
    )
