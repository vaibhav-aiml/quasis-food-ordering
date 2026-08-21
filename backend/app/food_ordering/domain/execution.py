"""Execution status and step result domain models for food ordering."""

from enum import Enum
from pydantic import BaseModel, Field

from app.food_ordering.domain.plan import ExecutionStepType


class ExecutionStatus(str, Enum):
    """Overall state of the automation plan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED_FOR_CLARIFICATION = "paused_for_clarification"
    READY_FOR_PAYMENT = "ready_for_payment"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepExecutionResult(BaseModel):
    """Result report for an individual automated step executed on device."""

    step_id: int = Field(ge=1)
    step_type: ExecutionStepType
    success: bool
    observed_screen: str | None = None
    message: str | None = None
    screenshot_ref: str | None = None


class FoodExecutionState(BaseModel):
    """Full execution state tracking on-device automation progress."""

    plan_id: str = Field(min_length=1)
    current_step_id: int = Field(default=1, ge=1)
    status: ExecutionStatus = ExecutionStatus.PENDING
    completed_steps: list[StepExecutionResult] = Field(default_factory=list)
    ready_for_payment: bool = False
    error_message: str | None = None
