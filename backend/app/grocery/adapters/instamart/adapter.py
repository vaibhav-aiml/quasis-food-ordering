"""Instamart store adapter — Phase 7: mocked data only, no real automation.

See ``app.grocery.adapters.zepto.adapter`` for the full design rationale shared
by all three mock adapters — not repeated here to avoid duplication.
"""

from app.grocery.adapters._mock_data import generate_mock_results, mock_add_to_cart, mock_checkout
from app.grocery.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.grocery.domain.raw_product_result import RawProductResult

STORE_ID = "instamart"

_PRICE_OFFSET = 2.5
_ETA_MINUTES = 25


class InstamartAdapter:
    """Mock Instamart integration. Satisfies the StoreAdapter protocol structurally."""

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
