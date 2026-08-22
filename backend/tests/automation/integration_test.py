"""End-to-end integration test for the Python uiautomator2 food ordering automation flow."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.food_ordering.domain.intent import FoodItemRequest
from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep
from app.main import create_app


def test_full_e2e_python_automation_via_api():
    app = create_app()
    client = TestClient(app)

    # 1. Register a realistic OrderPlan in the backend
    sample_plan = OrderPlan(
        plan_id="e2e_plan_test_999",
        target_app="swiggy",
        restaurant_name="Domino's Pizza",
        items=[
            FoodItemRequest(name="Margherita Pizza", quantity=2, customization_notes=["Cheese Burst"]),
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

    # Pre-register plan in execution service
    from app.core.dependencies import get_execution_service
    service = get_execution_service()
    service.register_plan(sample_plan)

    # 2. Trigger execution with uiautomator2 engine
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

        response = client.post(
            "/v1/food/order/execute",
            json={
                "plan_id": "e2e_plan_test_999",
                "device_id": "emulator-5554",
                "engine": "uiautomator2",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready_for_payment"
        assert data["current_step"] == "STOP_FOR_PAYMENT"
        assert data["steps_completed"] == 8
        assert data["total_steps"] == 8

        # 3. Query execution status via GET /order/status/{exec_id}
        exec_id = data["execution_id"]
        status_res = client.get(f"/v1/food/order/status/{exec_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "ready_for_payment"
        assert status_data["result"] == "STOPPED_AT_PAYMENT"
