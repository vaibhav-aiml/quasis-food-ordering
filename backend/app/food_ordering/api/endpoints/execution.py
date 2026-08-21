"""Execution management endpoints for food ordering.

API 1: POST /execute  — Start executing a plan on an Android device.
API 2: GET  /status/{execution_id} — Check execution progress.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_execution_service
from app.food_ordering.services.execution_service import ExecutionService, ExecutionSession

router = APIRouter(prefix="/order", tags=["food-execution"])


class ExecuteRequest(BaseModel):
    """Request payload for starting plan execution."""

    plan_id: str = Field(min_length=1, description="ID of a previously generated OrderPlan.")
    device_id: str = Field(min_length=1, description="Target Android device identifier.")
    auto_execute: bool = Field(default=True, description="If True, execute steps automatically.")


class ExecuteResponse(BaseModel):
    """Response returned when execution is started."""

    execution_id: str
    status: str
    current_step: str | None
    steps_completed: int
    total_steps: int
    message: str


class StatusResponse(BaseModel):
    """Response returned for execution status queries."""

    execution_id: str
    status: str
    current_step: str | None
    steps_completed: int
    total_steps: int
    result: str | None
    message: str


@router.post("/execute", response_model=ExecuteResponse, status_code=200)
def execute_order_plan(
    payload: ExecuteRequest,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> ExecuteResponse:
    """Start executing a previously generated order plan on a device.

    The execution enforces the safety boundary: plans with
    ``stop_before_payment=True`` will result in ``STOPPED_AT_PAYMENT``.
    """
    try:
        session = service.start_execution(
            plan_id=payload.plan_id,
            device_id=payload.device_id,
            auto_execute=payload.auto_execute,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plan '{payload.plan_id}' not found")

    return ExecuteResponse(
        execution_id=session.execution_id,
        status=session.status.value,
        current_step=session.current_step,
        steps_completed=session.steps_completed,
        total_steps=session.total_steps,
        message=session.message,
    )


@router.get("/status/{execution_id}", response_model=StatusResponse, status_code=200)
def get_execution_status(
    execution_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> StatusResponse:
    """Check the current status and progress of an ongoing execution."""
    try:
        session = service.get_status(execution_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{execution_id}' not found",
        )

    return StatusResponse(
        execution_id=session.execution_id,
        status=session.status.value,
        current_step=session.current_step,
        steps_completed=session.steps_completed,
        total_steps=session.total_steps,
        result=session.result,
        message=session.message,
    )
