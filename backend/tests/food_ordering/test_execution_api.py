"""Tests for food ordering execution API endpoints (APIs 1 & 2)."""

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_execution_service
from app.food_ordering.domain.plan import ExecutionStepType, OrderPlan, OrderStep
from app.food_ordering.domain.intent import FoodItemRequest
from app.food_ordering.services.execution_service import ExecutionService
from app.main import create_app


def _make_sample_plan(plan_id: str = "plan_test_001") -> OrderPlan:
    """Build a minimal plan with safety stop for testing."""
    return OrderPlan(
        plan_id=plan_id,
        target_app="swiggy",
        restaurant_name="Meghana Foods",
        items=[FoodItemRequest(name="chicken biryani", quantity=1)],
        steps=[
            OrderStep(
                step_id=1,
                step_type=ExecutionStepType.LAUNCH_APP,
                target_value="in.swiggy.android",
                expected_screen="home",
            ),
            OrderStep(
                step_id=2,
                step_type=ExecutionStepType.SEARCH_RESTAURANT,
                target_value="Meghana Foods",
                expected_screen="home",
            ),
            OrderStep(
                step_id=3,
                step_type=ExecutionStepType.STOP_FOR_PAYMENT,
                expected_screen="checkout",
            ),
        ],
        stop_before_payment=True,
    )


@pytest.fixture
def execution_service() -> ExecutionService:
    svc = ExecutionService()
    svc.register_plan(_make_sample_plan("plan_test_001"))
    return svc


@pytest.fixture
def client(execution_service: ExecutionService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_execution_service] = lambda: execution_service
    return TestClient(app)


class TestExecuteOrderPlan:
    """Tests for POST /v1/food/order/execute."""

    def test_execute_valid_plan(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/execute",
            json={"plan_id": "plan_test_001", "device_id": "android_test_1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"].startswith("exec_")
        assert data["total_steps"] == 3
        assert data["message"] != ""

    def test_execute_enforces_safety_boundary(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/execute",
            json={"plan_id": "plan_test_001", "device_id": "android_test_1", "auto_execute": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready_for_payment"
        assert data["current_step"] == "STOP_FOR_PAYMENT"
        assert data["steps_completed"] == 3

    def test_execute_unknown_plan_returns_404(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/execute",
            json={"plan_id": "plan_nonexistent", "device_id": "android_test_1"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_execute_missing_fields_returns_422(self, client: TestClient) -> None:
        response = client.post("/v1/food/order/execute", json={})
        assert response.status_code == 422


class TestGetExecutionStatus:
    """Tests for GET /v1/food/order/status/{execution_id}."""

    def test_status_after_execution(self, client: TestClient) -> None:
        # First, start an execution
        exec_response = client.post(
            "/v1/food/order/execute",
            json={"plan_id": "plan_test_001", "device_id": "android_test_1"},
        )
        exec_id = exec_response.json()["execution_id"]

        # Then, check its status
        status_response = client.get(f"/v1/food/order/status/{exec_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["execution_id"] == exec_id
        assert data["result"] == "STOPPED_AT_PAYMENT"

    def test_status_unknown_execution_returns_404(self, client: TestClient) -> None:
        response = client.get("/v1/food/order/status/exec_nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
