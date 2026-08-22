"""Tests for automation plan orchestrator."""

from unittest.mock import MagicMock, patch
import pytest

from app.automation.exceptions import PaymentScreenSafetyHalt
from app.automation.orchestrator import cancel_order, execute_order_plan, get_order_status
from app.food_ordering.domain.execution import ExecutionStatus
from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep


def _create_sample_plan(stop_before_payment: bool = True) -> OrderPlan:
    return OrderPlan(
        plan_id="test_plan_001",
        restaurant_name="Domino's Pizza",
        steps=[
            OrderStep(step_id=1, step_type=ExecutionStepType.LAUNCH_APP, expected_screen="home"),
            OrderStep(step_id=2, step_type=ExecutionStepType.SEARCH_RESTAURANT, target_value="Domino's Pizza", expected_screen="search_results"),
            OrderStep(step_id=3, step_type=ExecutionStepType.SELECT_RESTAURANT, target_value="Domino's Pizza", expected_screen="restaurant_menu"),
            OrderStep(step_id=4, step_type=ExecutionStepType.ADD_TO_CART, target_value="Margherita Pizza", parameters={"quantity": 1}, expected_screen="restaurant_menu"),
            OrderStep(step_id=5, step_type=ExecutionStepType.VIEW_CART, expected_screen="cart"),
            OrderStep(step_id=6, step_type=ExecutionStepType.STOP_FOR_PAYMENT, expected_screen="payment"),
        ],
        stop_before_payment=stop_before_payment,
    )


def test_execute_order_plan_stops_at_payment_milestone():
    mock_d = MagicMock()
    plan = _create_sample_plan(stop_before_payment=True)

    with patch("app.automation.orchestrator._dispatch_step", side_effect=[
        True,  # LAUNCH_APP
        True,  # SEARCH_RESTAURANT
        True,  # SELECT_RESTAURANT
        True,  # ADD_TO_CART
        True,  # VIEW_CART
        PaymentScreenSafetyHalt(screenshot_path="/tmp/payment_screen.png"),  # STOP_FOR_PAYMENT
    ]):
        result = execute_order_plan(plan, device_instance=mock_d)
        assert result["status"] == ExecutionStatus.READY_FOR_PAYMENT.value
        assert result["result"] == "STOPPED_AT_PAYMENT"
        assert result["steps_completed"] == 6

        # Check status retrieval
        status = get_order_status(result["execution_id"])
        assert status["status"] == ExecutionStatus.READY_FOR_PAYMENT.value


def test_execute_order_plan_handles_step_failure():
    mock_d = MagicMock()
    plan = _create_sample_plan()

    with patch("app.automation.orchestrator._dispatch_step", return_value=False):
        result = execute_order_plan(plan, device_instance=mock_d)
        assert result["status"] == ExecutionStatus.FAILED.value
        assert "STEP_FAILED" in result["result"]


def test_cancel_order():
    mock_d = MagicMock()
    plan = _create_sample_plan()

    with patch("app.automation.orchestrator._dispatch_step", return_value=True), \
         patch("app.automation.orchestrator.stop_before_payment", return_value={"status": "STOPPED_AT_PAYMENT"}):
        result = execute_order_plan(plan, device_instance=mock_d)
        exec_id = result["execution_id"]

        cancelled = cancel_order(exec_id)
        assert cancelled is True
        status = get_order_status(exec_id)
        assert status["cancelled"] is True
        assert status["status"] == ExecutionStatus.FAILED.value
