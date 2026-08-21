"""In-memory restaurant catalog service for food ordering.

Seeded with realistic Indian restaurant data for immediate API testing.
Replace with an external data source (Swiggy/Zomato API, database) in
production.
"""

import logging
from app.food_ordering.domain.restaurant import (
    CustomizationGroup,
    CustomizationOption,
    MenuItem,
    Restaurant,
)

_logger = logging.getLogger("app.food_ordering.services.restaurant")


def _build_seed_catalog() -> list[Restaurant]:
    """Build a realistic seed catalog of Indian restaurants."""
    return [
        Restaurant(
            restaurant_id="rest_meghana",
            name="Meghana Foods",
            rating=4.5,
            eta_minutes=35,
            cuisines=["Indian", "Biryani", "Andhra"],
            address="Indiranagar, Bangalore",
            is_open=True,
            menu=[
                MenuItem(
                    item_id="item_meg_001",
                    name="Chicken Biryani",
                    description="Hyderabadi style dum biryani with raita",
                    price_inr=250.0,
                    is_veg=False,
                    customization_groups=[
                        CustomizationGroup(
                            group_id="cg_meg_raita",
                            group_name="Raita",
                            min_selection=0,
                            max_selection=1,
                            options=[
                                CustomizationOption(
                                    option_id="opt_extra_raita",
                                    name="Extra Raita",
                                    price_delta_inr=30.0,
                                ),
                            ],
                        ),
                    ],
                ),
                MenuItem(
                    item_id="item_meg_002",
                    name="Mutton Biryani",
                    description="Slow-cooked mutton dum biryani",
                    price_inr=350.0,
                    is_veg=False,
                ),
                MenuItem(
                    item_id="item_meg_003",
                    name="Paneer Biryani",
                    description="Cottage cheese dum biryani",
                    price_inr=220.0,
                    is_veg=True,
                ),
            ],
        ),
        Restaurant(
            restaurant_id="rest_saravana",
            name="Saravana Bhavan",
            rating=4.3,
            eta_minutes=25,
            cuisines=["South Indian", "Vegetarian"],
            address="MG Road, Bangalore",
            is_open=True,
            menu=[
                MenuItem(
                    item_id="item_sar_001",
                    name="Masala Dosa",
                    description="Crispy dosa with potato masala",
                    price_inr=120.0,
                    is_veg=True,
                ),
                MenuItem(
                    item_id="item_sar_002",
                    name="Idli Sambar",
                    description="Steamed rice cakes with sambar",
                    price_inr=80.0,
                    is_veg=True,
                ),
                MenuItem(
                    item_id="item_sar_003",
                    name="Filter Coffee",
                    description="Traditional South Indian filter coffee",
                    price_inr=50.0,
                    is_veg=True,
                ),
            ],
        ),
        Restaurant(
            restaurant_id="rest_ccd",
            name="Cafe Coffee Day",
            rating=4.0,
            eta_minutes=20,
            cuisines=["Cafe", "Beverages", "Snacks"],
            address="Koramangala, Bangalore",
            is_open=True,
            menu=[
                MenuItem(
                    item_id="item_ccd_001",
                    name="Cappuccino",
                    description="Classic Italian cappuccino",
                    price_inr=180.0,
                    is_veg=True,
                ),
                MenuItem(
                    item_id="item_ccd_002",
                    name="Cold Coffee",
                    description="Iced coffee blended with ice cream",
                    price_inr=200.0,
                    is_veg=True,
                ),
            ],
        ),
        Restaurant(
            restaurant_id="rest_paradise",
            name="Paradise Biryani",
            rating=4.4,
            eta_minutes=40,
            cuisines=["Indian", "Biryani", "Hyderabadi"],
            address="HSR Layout, Bangalore",
            is_open=True,
            menu=[
                MenuItem(
                    item_id="item_par_001",
                    name="Chicken Biryani",
                    description="Signature Paradise chicken biryani",
                    price_inr=280.0,
                    is_veg=False,
                ),
                MenuItem(
                    item_id="item_par_002",
                    name="Veg Biryani",
                    description="Mixed vegetable dum biryani",
                    price_inr=200.0,
                    is_veg=True,
                ),
            ],
        ),
    ]


class RestaurantService:
    """In-memory restaurant catalog with search and menu retrieval."""

    def __init__(self) -> None:
        self._restaurants: dict[str, Restaurant] = {}
        for r in _build_seed_catalog():
            self._restaurants[r.restaurant_id] = r

    def search(
        self,
        query: str | None = None,
        location: str | None = None,
    ) -> list[Restaurant]:
        """Search restaurants by name, cuisine, or location.

        Performs case-insensitive substring matching. If both query and
        location are provided, results must match both.
        """
        results = list(self._restaurants.values())

        if query:
            q = query.lower()
            results = [
                r for r in results
                if q in r.name.lower()
                or any(q in c.lower() for c in r.cuisines)
            ]

        if location:
            loc = location.lower()
            results = [
                r for r in results
                if r.address and loc in r.address.lower()
            ]

        # Strip menus from search results to keep responses lightweight
        return [
            r.model_copy(update={"menu": []})
            for r in results
        ]

    def get_menu(self, restaurant_id: str) -> Restaurant:
        """Get a restaurant with its full menu.

        Raises:
            KeyError: If restaurant_id is not found.
        """
        restaurant = self._restaurants.get(restaurant_id)
        if restaurant is None:
            raise KeyError(f"Restaurant '{restaurant_id}' not found")
        return restaurant
