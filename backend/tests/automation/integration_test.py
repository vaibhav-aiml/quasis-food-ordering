"""End-to-end integration test for the Python uiautomator2 food ordering automation flow."""

from unittest.mock import MagicMock, patch

from app.automation.orchestrator import cancel_order, execute_order_plan, get_order_status
from app.food_ordering.domain.execution import ExecutionStatus
from app.food_ordering.domain.intent import FoodItemRequest
from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep


def test_full_e2e_python_automation_flow():
    # 1. Construct a realistic multi-step OrderPlan
    sample_plan = OrderPlan(
        plan_id="e2e_plan_test_999",
        target_app="swiggy",
        restaurant_name="Domino's Pizza",
        items=[
            FoodItemRequest(name="Margherita Pizza", quantity=2, customizations=["Cheese Burst"]),
        ],
        steps=[
            OrderStep(step_id=1, step_type=ExecutionStepType.LAUNCH_APP, expected_screen="home"),
            OrderStep(step_id=2, step_type=ExecutionStepType.SEARCH_RESTAURANT, target_value="Domino's Pizza", expected_screen="search_results"),
            OrderStep(step_id=3, step_type=ExecutionStepType.SELECT_RESTAURANT, target_value="Domino's Pizza", expected_screen="restaurant_menu"),
            OrderStep(step_id=4, step_type=ExecutionStepType.SEARCH_MENU_ITEM, target_value="Margherita Pizza", expected_screen="restaurant_menu"),
            OrderStep(
                step_id=5,
                step_type=ExecutionStepType.ADD_TO_CART,
                target_value="Margherita Pizza",
                parameters={"quantity": 2, "customizations": ["Cheese Burst"]},
                expected_screen="restaurant_menu",
            ),
            OrderStep(step_id=6, step_type=ExecutionStepType.VIEW_CART, expected_screen="cart"),
            OrderStep(step_id=7, step_type=ExecutionStepType.PROCEED_TO_CHECKOUT, expected_screen="checkout"),
            OrderStep(step_id=8, step_type=ExecutionStepType.STOP_FOR_PAYMENT, expected_screen="payment"),
        ],
        stop_before_payment=True,
    )

    # 2. Trigger execution with uiautomator2 engine mocks
    mock_device = MagicMock()
    with patch("app.automation.orchestrator.connect_device", return_value=mock_device), \
         patch("app.automation.orchestrator.launch_swiggy", return_value=True), \
         patch("app.automation.orchestrator.search_restaurant", return_value=True), \
         patch("app.automation.orchestrator.select_restaurant", return_value=True), \
         patch("app.automation.orchestrator.search_menu_item", return_value=True), \
         patch("app.automation.orchestrator.add_to_cart", return_value=True), \
         patch("app.automation.orchestrator.view_cart", return_value=True), \
         patch("app.automation.orchestrator.proceed_to_checkout", return_value={"status": "STOPPED_AT_PAYMENT"}), \
         patch("app.automation.orchestrator.stop_before_payment", return_value={"status": "STOPPED_AT_PAYMENT", "screenshot_path": "/tmp/cart.png"}):

        result = execute_order_plan(sample_plan, device_serial="emulator-5554")

        assert result["status"] == ExecutionStatus.READY_FOR_PAYMENT.value
        assert result["current_step"] == "STOP_FOR_PAYMENT"
        assert result["steps_completed"] == 8
        assert result["total_steps"] == 8

        # 3. Query execution status via get_order_status
        exec_id = result["execution_id"]
        status_data = get_order_status(exec_id)
        assert status_data is not None
        assert status_data["status"] == ExecutionStatus.READY_FOR_PAYMENT.value
        assert status_data["result"] == "STOPPED_AT_PAYMENT"
