"""In-memory execution management service for food ordering.

Manages the lifecycle of plan executions dispatched to Android devices.
Uses an in-memory dict store — swap for a real database behind the same
interface when ready for production.
"""

import hashlib
import logging
import time
from pydantic import BaseModel, Field

from app.food_ordering.domain.execution import ExecutionStatus
from app.food_ordering.domain.plan import OrderPlan

_logger = logging.getLogger("app.food_ordering.services.execution")


class ExecutionSession(BaseModel):
    """Full state of a single plan execution."""

    execution_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: str | None = None
    steps_completed: int = 0
    total_steps: int = 0
    result: str | None = None
    message: str = ""


class ExecutionService:
    """Manages plan execution sessions against Android devices.

    Safety invariant: if the plan has ``stop_before_payment=True`` the
    execution result will always be ``STOPPED_AT_PAYMENT``.
    """

    def __init__(self) -> None:
        self._store: dict[str, ExecutionSession] = {}
        self._plan_store: dict[str, OrderPlan] = {}

    # ------------------------------------------------------------------
    # Plan registration (called by plan endpoint or test setup)
    # ------------------------------------------------------------------

    def register_plan(self, plan: OrderPlan) -> None:
        """Store a plan so it can be referenced by execute."""
        self._plan_store[plan.plan_id] = plan

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_execution(
        self,
        plan_id: str,
        device_id: str,
        auto_execute: bool = True,
    ) -> ExecutionSession:
        """Start executing a plan on a device.

        Args:
            plan_id: ID of a previously generated OrderPlan.
            device_id: Target Android device identifier.
            auto_execute: If True, simulate immediate execution progress.

        Returns:
            ExecutionSession with current state.

        Raises:
            KeyError: If plan_id is not found.
        """
        plan = self._plan_store.get(plan_id)
        if plan is None:
            raise KeyError(f"Plan '{plan_id}' not found")

        exec_id = self._generate_id(plan_id)
        total = len(plan.steps)
        first_step = plan.steps[0].step_type.value if plan.steps else None

        if auto_execute and plan.stop_before_payment:
            # Simulate completed execution that stopped at payment
            session = ExecutionSession(
                execution_id=exec_id,
                plan_id=plan_id,
                device_id=device_id,
                status=ExecutionStatus.READY_FOR_PAYMENT,
                current_step="STOP_FOR_PAYMENT",
                steps_completed=total,
                total_steps=total,
                result="STOPPED_AT_PAYMENT",
                message="Order ready for payment confirmation",
            )
        else:
            session = ExecutionSession(
                execution_id=exec_id,
                plan_id=plan_id,
                device_id=device_id,
                status=ExecutionStatus.IN_PROGRESS,
                current_step=first_step,
                steps_completed=0,
                total_steps=total,
                message="Execution started successfully",
            )

        self._store[exec_id] = session
        _logger.info(
            "execution_started",
            extra={"execution_id": exec_id, "plan_id": plan_id, "device_id": device_id},
        )
        return session

    def get_status(self, execution_id: str) -> ExecutionSession:
        """Retrieve the current state of an execution.

        Raises:
            KeyError: If execution_id is not found.
        """
        session = self._store.get(execution_id)
        if session is None:
            raise KeyError(f"Execution '{execution_id}' not found")
        return session

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_id(seed: str) -> str:
        digest = hashlib.md5(f"{seed}-{time.time()}".encode()).hexdigest()[:12]
        return f"exec_{digest}"
