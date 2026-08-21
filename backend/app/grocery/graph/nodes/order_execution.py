"""Order Execution node — Phase 15: real add-to-cart + checkout via
injected adapters (Phase 14).
"""

from typing import Any, Mapping

from app.grocery.adapters.base import StoreAdapter
from app.grocery.adapters.types import CartActionResult
from app.grocery.domain.normalized_product import NormalizedProduct
from app.grocery.domain.raw_product_result import RawProductResult
from app.grocery.graph.state import GraphState


def _normalized_to_raw(normalized: NormalizedProduct) -> RawProductResult:
    """Bridges a ``NormalizedProduct`` back into the ``RawProductResult``
    shape ``StoreAdapter.add_to_cart`` expects.

    Phase 7's ``StoreAdapter`` interface (``base.py``) took
    ``product: RawProductResult`` for ``add_to_cart``, explicitly flagged
    there as provisional: "the eventually-correct parameter type (likely
    NormalizedProduct or RankedResult) doesn't exist until Phase 10/11."
    Now that those types exist, this IS that flagged decision point —
    resolved by bridging here, at the integration layer, rather than
    changing the Protocol. Changing ``StoreAdapter``'s signature now would
    cascade through every adapter (Phases 7/8/14) and their already-
    passing test suites for no functional benefit; this small conversion
    function is a far smaller, contained cost.
    """

    return RawProductResult(
        store_id=normalized.store_id,
        raw_title=normalized.product_name,
        raw_price=f"{normalized.price_inr:.2f}",
        raw_eta=f"{normalized.eta_minutes} mins",
        raw_quantity=f"{normalized.quantity:g} {normalized.unit}",
    )


def make_order_execution_node(adapters_by_id: Mapping[str, StoreAdapter]):
    def order_execution_node(state: GraphState) -> dict[str, Any]:
        outcome = state["approval_outcome"]
        basket = state["basket"]

        if outcome is None or basket is None or outcome.store_id is None:
            return {
                "status": "failed",
                "error_message": "No approved store/basket to order from.",
            }

        adapter = adapters_by_id.get(outcome.store_id)
        if adapter is None:
            return {
                "status": "failed",
                "error_message": f"No adapter available for store '{outcome.store_id}'.",
            }

        cart_results: list[CartActionResult] = [
            adapter.add_to_cart(_normalized_to_raw(ranked.product))
            for ranked in basket.matched_products
        ]

        if not all(result.success for result in cart_results):
            failed_items = [r.product_name for r in cart_results if not r.success]
            return {
                "cart_results": cart_results,
                "status": "failed",
                "error_message": f"Failed to add to cart: {', '.join(failed_items)}",
            }

        checkout_state = adapter.checkout()
        order_confirmation = {
            "store_id": outcome.store_id,
            "status": checkout_state.status,
            "message": checkout_state.message or "",
        }
        final_status = (
            "ready_for_payment" if checkout_state.status == "ready_for_payment" else "failed"
        )

        return {
            "cart_results": cart_results,
            "checkout_state": checkout_state,
            "order_confirmation": order_confirmation,
            "status": final_status,
        }

    return order_execution_node


def route_after_order_execution(state: GraphState) -> str:
    """Conditional edge (Phase 16 fix): only continue to the
    ``ready_for_payment`` terminal node when ``order_execution`` actually
    reached the real payment screen.

    Previously this was an unconditional edge straight to
    ``ready_for_payment_node``, which unconditionally overwrote
    ``status`` to ``"ready_for_payment"`` even when
    ``order_execution_node`` had just set ``status="failed"`` (cart
    failure, missing adapter/store, or a checkout that didn't reach the
    payment screen). That's a real bug for the FastAPI layer's contract
    (never report ``ready_for_payment`` unless checkout genuinely got
    there) and is corrected here rather than in the adapter/automation
    code itself.
    """

    return "ready_for_payment" if state["status"] == "ready_for_payment" else "failed"
