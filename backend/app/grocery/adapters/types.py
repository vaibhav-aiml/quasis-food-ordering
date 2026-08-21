"""Supporting types for the Store Adapter interface.

``SearchQuery``/``CartActionResult``/``CheckoutState`` aren't part of
Phase 0's fully field-level-detailed contract list (section 11 only
specced ``IntentRequest``, ``ProductRequest``, ``Constraints``,
``RawProductResult``, ``NormalizedProduct``, ``RankedResult``) — these
three exist because the ``StoreAdapter`` interface itself (section 6)
references them by name. They're intentionally minimal and provisional:
``CartActionResult``/``CheckoutState`` in particular are expected to be
revisited once Phase 14 (Order Executor) designs real add-to-cart/
checkout flows in detail.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.grocery.domain.product import ProductRequest


class SearchQuery(BaseModel):
    """What a Store Adapter is asked to search for.

    A thin wrapper around a product list, rather than a bare
    ``list[ProductRequest]``, specifically so search-scoped options (e.g.
    a future max-results cap) can be added later without changing every
    adapter's method signature.
    """

    products: list[ProductRequest] = Field(min_length=1)


class CartActionResult(BaseModel):
    """Result of an add-to-cart attempt.

    Provisional shape — Phase 14 owns the real design once cart/checkout
    flows are actually built against real store UIs.
    """

    store_id: str
    product_name: str
    success: bool
    message: str | None = None


class CheckoutState(BaseModel):
    """Result of a checkout attempt. Provisional shape — see ``CartActionResult``."""

    store_id: str
    status: Literal["pending", "ready_for_payment", "failed"]
    message: str | None = None
