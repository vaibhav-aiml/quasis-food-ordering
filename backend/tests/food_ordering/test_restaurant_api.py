"""Tests for food ordering restaurant API endpoints (APIs 3 & 4)."""

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_restaurant_service
from app.food_ordering.services.restaurant_service import RestaurantService
from app.main import create_app


@pytest.fixture
def restaurant_service() -> RestaurantService:
    return RestaurantService()


@pytest.fixture
def client(restaurant_service: RestaurantService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_restaurant_service] = lambda: restaurant_service
    return TestClient(app)


class TestSearchRestaurants:
    """Tests for GET /v1/food/restaurants/search."""

    def test_search_by_name(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/search", params={"query": "Meghana"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["restaurants"]) == 1
        assert data["restaurants"][0]["name"] == "Meghana Foods"
        assert data["restaurants"][0]["id"] == "rest_meghana"

    def test_search_by_cuisine(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/search", params={"query": "Biryani"})
        assert response.status_code == 200
        data = response.json()
        # Meghana Foods and Paradise Biryani both serve biryani
        names = {r["name"] for r in data["restaurants"]}
        assert "Meghana Foods" in names
        assert "Paradise Biryani" in names

    def test_search_by_location(self, client: TestClient) -> None:
        response = client.get(
            "/v1/food/restaurants/search",
            params={"query": "Coffee", "location": "Koramangala"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["restaurants"]) == 1
        assert data["restaurants"][0]["name"] == "Cafe Coffee Day"

    def test_search_no_results(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/search", params={"query": "NonexistentPlace"})
        assert response.status_code == 200
        data = response.json()
        assert data["restaurants"] == []

    def test_search_all_restaurants(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/search")
        assert response.status_code == 200
        data = response.json()
        assert len(data["restaurants"]) == 4

    def test_search_result_has_delivery_time(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/search", params={"query": "Meghana"})
        assert response.status_code == 200
        rest = response.json()["restaurants"][0]
        assert rest["delivery_time"] is not None
        assert "mins" in rest["delivery_time"]


class TestGetRestaurantMenu:
    """Tests for GET /v1/food/restaurants/{restaurant_id}/menu."""

    def test_get_menu_valid_restaurant(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/rest_meghana/menu")
        assert response.status_code == 200
        data = response.json()
        assert data["restaurant_id"] == "rest_meghana"
        assert data["restaurant_name"] == "Meghana Foods"
        assert len(data["menu"]) == 3

    def test_menu_item_has_price(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/rest_meghana/menu")
        biryani = next(
            item for item in response.json()["menu"]
            if item["name"] == "Chicken Biryani"
        )
        assert biryani["price"] == 250.0
        assert "Extra Raita" in biryani["customizations"]

    def test_menu_item_has_veg_flag(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/rest_saravana/menu")
        dosa = next(
            item for item in response.json()["menu"]
            if item["name"] == "Masala Dosa"
        )
        assert dosa["is_veg"] is True

    def test_get_menu_unknown_restaurant_returns_404(self, client: TestClient) -> None:
        response = client.get("/v1/food/restaurants/rest_nonexistent/menu")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
