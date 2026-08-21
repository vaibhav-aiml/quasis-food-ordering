"""Zepto store adapter — Phase 7: mocked data only, no real automation.

Real Appium-backed search/cart/checkout is wired in Phase 8. Until then,
this class exists so the StoreAdapter interface has a genuine, named
implementation to plan/orchestrate against, and so later phases can swap
this class's internals without changing its public shape.
"""

from app.grocery.adapters._mock_data import generate_mock_results, mock_add_to_cart, mock_checkout
from app.grocery.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.grocery.domain.raw_product_result import RawProductResult

STORE_ID = "zepto"

# Deterministic mock tuning — arbitrary but fixed, so Zepto is
# consistently the cheapest of the three mock stores and Blinkit/Instamart
# differ meaningfully from it. Purely a Phase 7 placeholder; has no
# bearing on real Zepto pricing once Phase 8 wires in real automation.
_PRICE_OFFSET = 0.0
_ETA_MINUTES = 15


class ZeptoAdapter:
    """Mock Zepto integration. Satisfies the StoreAdapter protocol structurally."""

    def get_store_id(self) -> str:
        return STORE_ID

    def is_available(self) -> bool:
        return True

    def search(self, query: SearchQuery) -> list[RawProductResult]:
        return generate_mock_results(
            STORE_ID, query.products, price_offset=_PRICE_OFFSET, eta_minutes=_ETA_MINUTES
        )

    def add_to_cart(self, product: RawProductResult) -> CartActionResult:
        return mock_add_to_cart(STORE_ID, product)

    def checkout(self) -> CheckoutState:
        return mock_checkout(STORE_ID)
