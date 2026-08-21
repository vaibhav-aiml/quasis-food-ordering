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
    intent: FoodOrderIntent | None = Field(
        default=None,
        description="Pre-extracted FoodOrderIntent to build plan from directly.",
    )


@router.post("/plan", response_model=FoodPlanResult, status_code=200)
def create_food_order_plan(
    payload: PlanCreateRequest,
    planner_agent: Annotated[FoodPlannerAgent, Depends(get_food_planner_agent)],
) -> FoodPlanResult:
    """Generate a step-by-step automation plan from text or validated intent."""
    if payload.intent is not None:
        return planner_agent.plan_from_intent(payload.intent)

    if payload.raw_text and payload.raw_text.strip():
        return planner_agent.plan_from_text(payload.raw_text)

    raise HTTPException(
        status_code=400,
        detail="Either 'raw_text' or 'intent' must be provided in request payload.",
    )
