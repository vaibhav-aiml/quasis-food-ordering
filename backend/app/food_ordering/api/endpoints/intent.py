"""Food intent parsing endpoint."""

from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_food_intent_agent
from app.food_ordering.agents.food_intent_agent import FoodIntentAgent
from app.food_ordering.domain.intent import FoodOrderIntent

router = APIRouter(prefix="/intent", tags=["food-intent"])


class IntentParseRequest(BaseModel):
    """Request payload for intent parsing."""

    raw_text: str | None = Field(default=None, description="Natural language food order request.")
    query: str | None = Field(default=None, description="Alias for raw_text.")

    def get_text(self) -> str:
        text = self.raw_text or self.query or ""
        if not text.strip():
            raise ValueError("Either 'raw_text' or 'query' must be provided.")
        return text.strip()


@router.post("/parse", response_model=FoodOrderIntent, status_code=200)
def parse_food_intent(
    payload: IntentParseRequest,
    intent_agent: Annotated[FoodIntentAgent, Depends(get_food_intent_agent)],
) -> FoodOrderIntent:
    """Parse a natural language food ordering request into structured intent."""
    return intent_agent.extract(payload.get_text())
