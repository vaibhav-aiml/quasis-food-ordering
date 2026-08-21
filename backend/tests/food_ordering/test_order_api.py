"""Tests for food ordering order management API endpoints (APIs 5, 6 & 7)."""

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_order_service
from app.food_ordering.services.order_service import OrderService
from app.main import create_app


@pytest.fixture
def order_service() -> OrderService:
    return OrderService()


@pytest.fixture
def client(order_service: OrderService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_order_service] = lambda: order_service
    return TestClient(app)


class TestOrderHistory:
    """Tests for GET /v1/food/orders/history."""

    def test_get_history_for_user(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/history", params={"user_id": "user_1"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["orders"]) == 3  # user_1 has 3 seed orders

    def test_get_history_with_limit(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/history", params={"user_id": "user_1", "limit": 1})
        assert response.status_code == 200
        data = response.json()
        assert len(data["orders"]) == 1

    def test_get_history_unknown_user_returns_empty(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/history", params={"user_id": "user_unknown"})
        assert response.status_code == 200
        data = response.json()
        assert data["orders"] == []

    def test_history_items_have_required_fields(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/history", params={"user_id": "user_1"})
        order = response.json()["orders"][0]
        assert "id" in order
        assert "restaurant" in order
        assert "items" in order
        assert "status" in order
        assert "timestamp" in order

    def test_history_is_sorted_most_recent_first(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/history", params={"user_id": "user_1"})
        orders = response.json()["orders"]
        timestamps = [o["timestamp"] for o in orders]
        assert timestamps == sorted(timestamps, reverse=True)


class TestTrackOrder:
    """Tests for GET /v1/food/orders/{order_id}/track."""

    def test_track_valid_order(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/order_003/track")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_003"
        assert data["status"] == "preparing"
        assert data["current_step"] == "Restaurant preparing food"
        assert data["estimated_delivery"] is not None

    def test_track_delivered_order(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/order_001/track")
        assert response.status_code == 200
        assert response.json()["status"] == "delivered"

    def test_track_unknown_order_returns_404(self, client: TestClient) -> None:
        response = client.get("/v1/food/orders/order_nonexistent/track")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCancelOrder:
    """Tests for POST /v1/food/order/cancel."""

    def test_cancel_preparing_order(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/cancel",
            json={"order_id": "order_003", "reason": "Changed my mind"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_003"
        assert data["status"] == "cancelled"
        assert data["message"] == "Order cancelled successfully"

    def test_cancel_delivered_order_returns_409(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/cancel",
            json={"order_id": "order_001", "reason": "Too late"},
        )
        assert response.status_code == 409
        assert "cannot be cancelled" in response.json()["detail"]

    def test_cancel_out_for_delivery_returns_409(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/cancel",
            json={"order_id": "order_004", "reason": "Delay"},
        )
        assert response.status_code == 409

    def test_cancel_unknown_order_returns_404(self, client: TestClient) -> None:
        response = client.post(
            "/v1/food/order/cancel",
            json={"order_id": "order_nonexistent", "reason": "Test"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_cancel_missing_fields_returns_422(self, client: TestClient) -> None:
        response = client.post("/v1/food/order/cancel", json={})
        assert response.status_code == 422
