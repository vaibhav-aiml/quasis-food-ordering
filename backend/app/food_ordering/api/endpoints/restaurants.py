"""Restaurant search and menu endpoints for food ordering.

API 3: GET /search            — Search restaurants by name, cuisine, location.
API 4: GET /{restaurant_id}/menu — Get full menu for a restaurant.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import get_restaurant_service
from app.food_ordering.domain.restaurant import MenuItem, Restaurant
from app.food_ordering.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants", tags=["food-restaurants"])


class RestaurantSummary(BaseModel):
    """Lightweight restaurant info returned in search results."""

    id: str
    name: str
    cuisine: list[str]
    rating: float | None
    delivery_time: str | None
    address: str | None


class SearchResponse(BaseModel):
    """Response payload for restaurant search."""

    restaurants: list[RestaurantSummary]


class MenuItemResponse(BaseModel):
    """Menu item with price and customization info."""

    id: str
    name: str
    price: float
    category: str | None = None
    description: str | None = None
    is_veg: bool = False
    customizations: list[str] = Field(default_factory=list)


class MenuResponse(BaseModel):
    """Response payload for a restaurant's menu."""

    restaurant_id: str
    restaurant_name: str
    menu: list[MenuItemResponse]


def _format_eta(eta: int | None) -> str | None:
    if eta is None:
        return None
    low = max(eta - 5, 5)
    high = eta + 5
    return f"{low}-{high} mins"


def _format_menu_item(item: MenuItem) -> MenuItemResponse:
    customizations: list[str] = []
    for group in item.customization_groups:
        for opt in group.options:
            customizations.append(opt.name)

    return MenuItemResponse(
        id=item.item_id,
        name=item.name,
        price=item.price_inr,
        description=item.description,
        is_veg=item.is_veg,
        customizations=customizations,
    )


@router.get("/search", response_model=SearchResponse, status_code=200)
def search_restaurants(
    service: Annotated[RestaurantService, Depends(get_restaurant_service)],
    query: str | None = Query(default=None, description="Search by name or cuisine"),
    location: str | None = Query(default=None, description="Filter by location"),
) -> SearchResponse:
    """Search for restaurants by name, cuisine, or location."""
    results = service.search(query=query, location=location)
    summaries = [
        RestaurantSummary(
            id=r.restaurant_id,
            name=r.name,
            cuisine=r.cuisines,
            rating=r.rating,
            delivery_time=_format_eta(r.eta_minutes),
            address=r.address,
        )
        for r in results
    ]
    return SearchResponse(restaurants=summaries)


@router.get("/{restaurant_id}/menu", response_model=MenuResponse, status_code=200)
def get_restaurant_menu(
    restaurant_id: str,
    service: Annotated[RestaurantService, Depends(get_restaurant_service)],
) -> MenuResponse:
    """Get the full menu of a specific restaurant."""
    try:
        restaurant = service.get_menu(restaurant_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Restaurant '{restaurant_id}' not found",
        )

    return MenuResponse(
        restaurant_id=restaurant.restaurant_id,
        restaurant_name=restaurant.name,
        menu=[_format_menu_item(item) for item in restaurant.menu],
    )
