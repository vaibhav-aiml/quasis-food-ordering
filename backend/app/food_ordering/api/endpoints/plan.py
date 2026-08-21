"""Food order plan generation endpoint."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_food_planner_agent
from app.food_ordering.agents.food_planner_agent import (
    FoodPlanResult,
    FoodPlannerAgent,
)
from app.food_ordering.domain.intent import FoodOrderIntent

router = APIRouter(prefix="/order", tags=["food-plan"])


class PlanCreateRequest(BaseModel):
    """Request payload for order plan creation."""

    raw_text: str | None = Field(
        default=None,
        description="Raw user request string to parse and plan from.",
    )
    query: str | None = Field(
        default=None,
        description="Alias for raw_text.",
    )
    intent: FoodOrderIntent | None = Field(
        default=None,
        description="Pre-extracted FoodOrderIntent to build plan from directly.",
    )

    def get_text(self) -> str | None:
        text = self.raw_text or self.query
        return text.strip() if text and text.strip() else None


@router.post("/plan", response_model=FoodPlanResult, status_code=200)
def create_food_order_plan(
    payload: PlanCreateRequest,
    planner_agent: Annotated[FoodPlannerAgent, Depends(get_food_planner_agent)],
) -> FoodPlanResult:
    """Generate a step-by-step automation plan from text or validated intent."""
    if payload.intent is not None:
        return planner_agent.plan_from_intent(payload.intent)

    text = payload.get_text()
    if text:
        return planner_agent.plan_from_text(text)

    raise HTTPException(
        status_code=400,
        detail="Either 'raw_text', 'query', or 'intent' must be provided in request payload.",
    )
