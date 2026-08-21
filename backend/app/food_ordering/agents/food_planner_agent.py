"""Food Ordering Planner Agent.

Orchestrates intent extraction and deterministic execution planning into a
unified pipeline.
"""

import logging
from pydantic import BaseModel

from app.food_ordering.agents.food_intent_agent import FoodIntentAgent
from app.food_ordering.domain.intent import FoodOrderIntent
from app.food_ordering.domain.plan import OrderPlan
from app.food_ordering.services.plan_builder import FoodPlanBuilder

_logger = logging.getLogger("app.food_ordering.agents.planner")


class FoodPlanResult(BaseModel):
    """Result containing both the parsed intent and the compiled plan."""

    intent: FoodOrderIntent
    plan: OrderPlan | None
    ready_to_automate: bool
    status_message: str


class FoodPlannerAgent:
    """Combines intent extraction with deterministic order plan generation."""

    def __init__(
        self,
        intent_agent: FoodIntentAgent,
        plan_builder: FoodPlanBuilder,
    ) -> None:
        self._intent_agent = intent_agent
        self._plan_builder = plan_builder

    def plan_from_text(self, raw_text: str) -> FoodPlanResult:
        """Parse raw user request and produce an execution plan.

        Args:
            raw_text: Raw user request string.

        Returns:
            FoodPlanResult with parsed intent and compiled plan (if actionable).
        """
        intent = self._intent_agent.extract(raw_text)
        return self.plan_from_intent(intent)

    def plan_from_intent(self, intent: FoodOrderIntent) -> FoodPlanResult:
        """Compile a plan directly from a validated FoodOrderIntent.

        Args:
            intent: A validated FoodOrderIntent.

        Returns:
            FoodPlanResult with parsed intent and compiled plan.
        """
        if intent.needs_clarification:
            return FoodPlanResult(
                intent=intent,
                plan=None,
                ready_to_automate=False,
                status_message=intent.clarification_reason or "Clarification needed.",
            )

        plan = self._plan_builder.build_plan(intent)
        return FoodPlanResult(
            intent=intent,
            plan=plan,
            ready_to_automate=True,
            status_message="Order plan created successfully and ready for automation.",
        )
