"""Shared deterministic mock-data generation for Phase 7's adapters.

Private to the adapters package (leading underscore) — not part of the
public interface, just internal DRY plumbing so the three concrete
adapters don't each reimplement the same pricing formula. Every adapter
still has its own named class and its own store-specific price/ETA
offset, so search results genuinely differ across stores — meaningful for
Ranking, once it's real (Phase 11).

Deliberately does NOT import from ``app.graph.mocks`` (Phase 5's
graph-scoped mock) even though the spirit is similar: ``adapters/`` must
not depend on ``graph/`` per the Phase 0 dependency graph (§9) — the
dependency only ever flows the other way.
"""

from app.adapters.types import CartActionResult, CheckoutState
from app.domain.product import ProductRequest
from app.domain.raw_product_result import RawProductResult


def generate_mock_results(
    store_id: str,
    products: list[ProductRequest],
    *,
    price_offset: float,
    eta_minutes: int,
) -> list[RawProductResult]:
    """Deterministic, no-randomness mock search results.

    Price varies by product position (so a multi-item request produces
    different prices per item) plus a per-store offset (so results differ
    meaningfully across stores).
    """

    results: list[RawProductResult] = []
    for index, product in enumerate(products):
        base_price = 10.0 * (index + 1) + price_offset
        results.append(
            RawProductResult(
                store_id=store_id,
                raw_title=product.name,
                raw_price=f"{base_price:.2f}",
                raw_eta=f"{eta_minutes} mins",
                raw_quantity=f"{product.quantity:g} {product.unit}",
            )
        )
    return results


def mock_add_to_cart(store_id: str, product: RawProductResult) -> CartActionResult:
    return CartActionResult(
        store_id=store_id,
        product_name=product.raw_title,
        success=True,
        message="Mock: added to cart (Phase 7 — no real automation yet).",
    )


def mock_checkout(store_id: str) -> CheckoutState:
    return CheckoutState(
        store_id=store_id,
        status="ready_for_payment",
        message="Mock: checkout reached payment step (Phase 7 — no real automation yet).",
    )
