"""Orchestrator pipeline executing food order plans via Python uiautomator2 automation."""

import hashlib
import logging
import time
from typing import Any

from app.automation.device_manager import connect_device, is_device_connected
from app.automation.exceptions import (
    AutomationError,
    ClarificationRequired,
    OrderExecutionCancelled,
    PaymentScreenSafetyHalt,
)
from app.automation.safety_guard import is_payment_screen, stop_before_payment
from app.automation.swiggy_flows import (
    add_to_cart,
    detect_multiple_restaurants,
    launch_swiggy,
    proceed_to_checkout,
    search_menu_item,
    search_restaurant,
    select_restaurant,
    view_cart,
)
from app.food_ordering.domain.execution import ExecutionStatus
from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep

logger = logging.getLogger("app.automation.orchestrator")

# In-memory store for active execution records
_EXECUTION_STORE: dict[str, dict[str, Any]] = {}


def _generate_execution_id(plan_id: str) -> str:
    digest = hashlib.md5(f"{plan_id}-{time.time()}".encode()).hexdigest()[:12]
    return f"exec_{digest}"


def execute_order_plan(
    plan: OrderPlan,
    device_serial: str | None = None,
    device_instance: Any = None,
) -> dict[str, Any]:
    """Execute a structured OrderPlan against the target Android device.

    Args:
        plan: OrderPlan domain object containing sequential automation steps.
        device_serial: Optional Android device serial or IP:port.
        device_instance: Optional pre-connected device instance (useful for testing/mocks).

    Returns:
        Dictionary containing execution summary, status, and milestone metadata.
    """
    exec_id = _generate_execution_id(plan.plan_id)
    total_steps = len(plan.steps)

    session: dict[str, Any] = {
        "execution_id": exec_id,
        "plan_id": plan.plan_id,
        "device_id": device_serial or "auto-detected",
        "status": ExecutionStatus.IN_PROGRESS.value,
        "current_step": plan.steps[0].step_type.value if plan.steps else None,
        "steps_completed": 0,
        "total_steps": total_steps,
        "result": None,
        "message": "Execution started.",
        "start_time": time.time(),
        "cancelled": False,
        "step_logs": [],
    }
    _EXECUTION_STORE[exec_id] = session

    logger.info("Starting order execution %s for plan '%s'...", exec_id, plan.plan_id)

    # 1. Connect Device
    d = device_instance
    if d is None:
        try:
            d = connect_device(serial=device_serial)
        except Exception as e:
            session["status"] = ExecutionStatus.FAILED.value
            session["result"] = "DEVICE_CONNECTION_ERROR"
            session["message"] = f"Failed to connect to device: {e}"
            logger.error("Execution %s aborted: Device connection error: %s", exec_id, e)
            return session

    # 2. Sequential Step Execution
    for idx, step in enumerate(plan.steps):
        if session.get("cancelled", False):
            session["status"] = ExecutionStatus.FAILED.value
            session["result"] = "CANCELLED"
            session["message"] = "Execution was cancelled by user request."
            return session

        step_name = step.step_type.value
        session["current_step"] = step_name
        logger.info("Executing step [%s/%s]: %s", idx + 1, total_steps, step_name)
        step_start = time.time()

        try:
            success = _dispatch_step(d, step, plan)
            elapsed = round(time.time() - step_start, 2)
            session["step_logs"].append({
                "step_id": step.step_id,
                "step_type": step_name,
                "success": success,
                "duration_seconds": elapsed,
            })

            if not success and step.is_critical:
                session["status"] = ExecutionStatus.FAILED.value
                session["result"] = f"STEP_FAILED_{step_name}"
                session["message"] = f"Critical step '{step_name}' failed to execute."
                return session

            session["steps_completed"] = idx + 1

        except ClarificationRequired as clarify_err:
            logger.info("Clarification required at step '%s': %s", step_name, clarify_err.message)
            session["status"] = ExecutionStatus.PAUSED_FOR_CLARIFICATION.value
            session["result"] = "NEEDS_CLARIFICATION"
            session["current_step"] = step_name
            session["message"] = clarify_err.message
            session["clarification_options"] = clarify_err.options
            session["paused_at_step_index"] = idx
            session["device_instance"] = d  # Keep device reference for resume
            return session

        except PaymentScreenSafetyHalt as safety_err:
            logger.info("Payment safety halt caught: %s", safety_err)
            session["status"] = ExecutionStatus.READY_FOR_PAYMENT.value
            session["result"] = "STOPPED_AT_PAYMENT"
            session["current_step"] = "STOP_FOR_PAYMENT"
            session["steps_completed"] = total_steps
            session["message"] = "Automation stopped safely at payment screen for human takeover."
            session["screenshot_path"] = safety_err.screenshot_path
            return session

        except Exception as e:
            logger.error("Error executing step '%s': %s", step_name, e, exc_info=True)
            if step.is_critical:
                session["status"] = ExecutionStatus.FAILED.value
                session["result"] = f"ERROR_{step_name}"
                session["message"] = f"Step '{step_name}' encountered error: {e}"
                return session

    # 3. Final Milestone Resolution
    if plan.stop_before_payment:
        halt_info = stop_before_payment(d, plan_id=plan.plan_id)
        actual_on_payment = halt_info.get("actual_on_payment_screen", False)
        if actual_on_payment:
            session["status"] = ExecutionStatus.READY_FOR_PAYMENT.value
            session["result"] = "STOPPED_AT_PAYMENT"
            session["current_step"] = "STOP_FOR_PAYMENT"
            session["message"] = halt_info.get("message", "Order ready for payment confirmation.")
        else:
            # All steps completed but we're not actually at the payment screen
            session["status"] = ExecutionStatus.READY_FOR_PAYMENT.value
            session["result"] = "STOPPED_AT_PAYMENT"
            session["current_step"] = "STOP_FOR_PAYMENT"
            session["message"] = (
                "All automation steps completed. "
                "Please verify items in cart and proceed to payment on your device."
            )
        session["screenshot_path"] = halt_info.get("screenshot_path")
    else:
        session["status"] = ExecutionStatus.COMPLETED.value
        session["result"] = "ORDER_COMPLETED"
        session["message"] = "All automation steps completed successfully."

    return session


def _dispatch_step(d: Any, step: OrderStep, plan: OrderPlan) -> bool:
    """Route an individual OrderStep to its corresponding Swiggy flow function."""
    step_type = step.step_type
    params = step.parameters or {}

    if step_type == ExecutionStepType.LAUNCH_APP:
        return launch_swiggy(d, force_stop_first=params.get("force_stop", False))

    if step_type == ExecutionStepType.SEARCH_RESTAURANT:
        query = step.target_value or plan.restaurant_name or params.get("query", "")
        return search_restaurant(d, query=query)

    if step_type == ExecutionStepType.SELECT_RESTAURANT:
        name = step.target_value or plan.restaurant_name or params.get("name", "")
        restaurant_index = params.get("restaurant_index")
        # Check for multiple matching restaurants first
        try:
            detect_multiple_restaurants(d, name)
        except ClarificationRequired:
            raise  # Let orchestrator handle the clarification flow
        return select_restaurant(d, restaurant_name=name, restaurant_index=restaurant_index)

    if step_type == ExecutionStepType.SEARCH_MENU_ITEM:
        item = step.target_value or params.get("item_name", "")
        return search_menu_item(d, item_name=item)

    if step_type in (ExecutionStepType.SELECT_ITEM, ExecutionStepType.ADD_TO_CART):
        item_name = step.target_value or params.get("item_name", "")
        quantity = params.get("quantity", 1)
        customizations = params.get("customizations") or []
        if isinstance(customizations, str):
            customizations = [customizations]
        return add_to_cart(d, item_name=item_name, quantity=quantity, customizations=customizations)

    if step_type == ExecutionStepType.APPLY_CUSTOMIZATION:
        customizations = params.get("customizations") or [step.target_value] if step.target_value else []
        item_name = params.get("item_name") or (plan.items[0].name if plan.items else "")
        return add_to_cart(d, item_name=item_name, quantity=1, customizations=customizations)

    if step_type == ExecutionStepType.VIEW_CART:
        return view_cart(d)

    if step_type == ExecutionStepType.PROCEED_TO_CHECKOUT:
        res = proceed_to_checkout(d, stop_at_payment=plan.stop_before_payment)
        return res.get("status") in ("CHECKOUT_PROCEEDED", "STOPPED_AT_PAYMENT")

    if step_type == ExecutionStepType.STOP_FOR_PAYMENT:
        stop_before_payment(d, plan_id=plan.plan_id)
        raise PaymentScreenSafetyHalt(screenshot_path=None)

    logger.warning("Unrecognized step type: %s", step_type)
    return True


def get_order_status(execution_id: str) -> dict[str, Any]:
    """Retrieve the current state of an ongoing or completed execution session.

    Args:
        execution_id: Unique execution identifier.

    Returns:
        Dictionary with execution state details.

    Raises:
        KeyError: If execution_id is not found in store.
    """
    if execution_id not in _EXECUTION_STORE:
        raise KeyError(f"Execution ID '{execution_id}' not found.")
    return _EXECUTION_STORE[execution_id]


def cancel_order(execution_id: str) -> bool:
    """Request cancellation of an in-progress order execution.

    Args:
        execution_id: Unique execution identifier.

    Returns:
        True if cancelled, False otherwise.
    """
    if execution_id not in _EXECUTION_STORE:
        return False
    _EXECUTION_STORE[execution_id]["cancelled"] = True
    _EXECUTION_STORE[execution_id]["status"] = ExecutionStatus.FAILED.value
    _EXECUTION_STORE[execution_id]["result"] = "CANCELLED"
    return True


def resume_execution(
    execution_id: str,
    selection_index: int,
) -> dict[str, Any]:
    """Resume a paused execution after user clarification.

    Args:
        execution_id: Unique execution identifier.
        selection_index: Index of the user's selected option from clarification_options.

    Returns:
        Updated session dictionary.

    Raises:
        KeyError: If execution_id is not found.
        ValueError: If execution is not in a paused state.
    """
    if execution_id not in _EXECUTION_STORE:
        raise KeyError(f"Execution ID '{execution_id}' not found.")

    session = _EXECUTION_STORE[execution_id]

    if session.get("status") != ExecutionStatus.PAUSED_FOR_CLARIFICATION.value:
        raise ValueError(f"Execution '{execution_id}' is not paused for clarification.")

    paused_step_idx = session.get("paused_at_step_index")
    d = session.get("device_instance")

    if paused_step_idx is None or d is None:
        session["status"] = ExecutionStatus.FAILED.value
        session["result"] = "RESUME_FAILED"
        session["message"] = "Cannot resume: missing device instance or step index."
        return session

    # Update the step parameters with the user's selection
    options = session.get("clarification_options", [])
    if selection_index < 0 or selection_index >= len(options):
        session["status"] = ExecutionStatus.FAILED.value
        session["result"] = "INVALID_SELECTION"
        session["message"] = f"Invalid selection index {selection_index}. Available: {len(options)} options."
        return session

    selected = options[selection_index]
    logger.info("Resuming execution %s with selection: %s", execution_id, selected)

    # Clear clarification state
    session["status"] = ExecutionStatus.IN_PROGRESS.value
    session["result"] = None
    session["message"] = f"Resuming with selection: {selected.get('display', selected.get('name', ''))}"
    session.pop("clarification_options", None)
    session.pop("paused_at_step_index", None)

    # Get the plan to continue executing from the paused step
    plan_id = session.get("plan_id")
    # We need to re-import here to get the plan store
    # For now, just select the restaurant directly and continue
    try:
        restaurant_name = selected.get("name", "")
        restaurant_idx = selected.get("index", 0)
        select_restaurant(d, restaurant_name=restaurant_name, restaurant_index=restaurant_idx)
        session["steps_completed"] = paused_step_idx + 1
        session["message"] = f"Selected restaurant: {selected.get('display', restaurant_name)}"
        logger.info("Restaurant selection resumed successfully.")
    except Exception as e:
        logger.error("Failed to select restaurant after clarification: %s", e)
        session["status"] = ExecutionStatus.FAILED.value
        session["result"] = "RESUME_SELECTION_FAILED"
        session["message"] = f"Failed to select restaurant: {e}"

    return session
