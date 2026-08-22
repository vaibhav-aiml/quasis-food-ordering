"""Standalone smoke test script for Swiggy food ordering automation on a real Android device.

Usage:
    python backend/scripts/smoke_test_swiggy_automation.py [--serial <device_serial>]
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_test")


def run_smoke_test(serial: str | None = None) -> None:
    from app.automation.actions import take_screenshot
    from app.automation.device_manager import connect_device, get_device_info, is_device_connected
    from app.automation.orchestrator import execute_order_plan
    from app.automation.safety_guard import stop_before_payment
    from app.food_ordering.domain.intent import FoodItemRequest
    from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep

    logger.info("=== STEP 1: Connecting to Android Device ===")
    try:
        d = connect_device(serial=serial)
    except Exception as e:
        logger.error("Failed to connect to device: %s", e)
        logger.info("Ensure USB debugging is enabled and 'adb devices' shows your device.")
        sys.exit(1)

    info = get_device_info(d)
    logger.info("Device connected: %s", info)

    logger.info("\n=== STEP 2: Creating Test Order Plan ===")
    plan = OrderPlan(
        plan_id=f"smoke_test_{int(time.time())}",
        target_app="swiggy",
        restaurant_name="Domino's Pizza",
        items=[
            FoodItemRequest(name="Margherita Pizza", quantity=1, customization_notes=[]),
        ],
        steps=[
            OrderStep(step_id=1, step_type=ExecutionStepType.LAUNCH_APP, expected_screen="home"),
            OrderStep(step_id=2, step_type=ExecutionStepType.SEARCH_RESTAURANT, target_value="Domino's Pizza", expected_screen="search_results"),
            OrderStep(step_id=3, step_type=ExecutionStepType.SELECT_RESTAURANT, target_value="Domino's Pizza", expected_screen="restaurant_menu"),
            OrderStep(step_id=4, step_type=ExecutionStepType.SEARCH_MENU_ITEM, target_value="Margherita Pizza", expected_screen="restaurant_menu"),
            OrderStep(step_id=5, step_type=ExecutionStepType.ADD_TO_CART, target_value="Margherita Pizza", parameters={"quantity": 1}, expected_screen="restaurant_menu"),
            OrderStep(step_id=6, step_type=ExecutionStepType.VIEW_CART, expected_screen="cart"),
            OrderStep(step_id=7, step_type=ExecutionStepType.STOP_FOR_PAYMENT, expected_screen="payment"),
        ],
        stop_before_payment=True,
    )

    logger.info("\n=== STEP 3: Executing Order Plan via uiautomator2 ===")
    result = execute_order_plan(plan, device_instance=d)

    logger.info("\n=== EXECUTION SUMMARY ===")
    logger.info("Status: %s", result.get("status"))
    logger.info("Result: %s", result.get("result"))
    logger.info("Steps Completed: %s / %s", result.get("steps_completed"), result.get("total_steps"))
    logger.info("Message: %s", result.get("message"))
    if result.get("screenshot_path"):
        logger.info("Safety Screenshot Saved: %s", result.get("screenshot_path"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Swiggy automation smoke test.")
    parser.add_argument("--serial", type=str, default=None, help="Target Android device serial or IP:port")
    args = parser.parse_args()

    run_smoke_test(serial=args.serial)
