"""End-to-End LangGraph Shopping Agent with Real Blinkit Appium Adapter.

Demonstrates the complete workflow:
  User Request -> Intent Understanding -> Planning -> Real Blinkit Search
  -> Normalization -> Ranking -> Candidate Selection -> Explicit Approval
  -> Real Blinkit Add to Cart -> Real Blinkit Checkout -> STOP at Payment Screen.

Payment confirmation is NEVER automated.
"""

import argparse
import sys
import uuid

# Configure UTF-8 for console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from langgraph.types import Command

from app.grocery.automation.driver_manager import DriverManager
from app.core.config import Settings
from app.core.dependencies import (
    create_blinkit_appium_adapter,
    get_intent_agent,
    get_recommendation_generator,
)
from app.grocery.graph.state import initial_state
from app.grocery.graph.workflow import build_graph
from app.grocery.processing.recommendation_selection import select_best_store


def run_e2e_blinkit(
    query_text: str,
    mode: str = "full",
    auto_approve: bool = False,
    product_index: int | None = None,
) -> None:
    settings = Settings(
        store_mode="real",
        blinkit_store_mode="real",
        zepto_store_mode="mock",
        instamart_store_mode="mock",
    )

    print("=" * 65)
    print("LANGGRAPH -> REAL BLINKIT APPIUM END-TO-END WORKFLOW")
    print("=" * 65)
    print(f"User Request: '{query_text}'")
    print(f"Execution Mode: {mode.upper()}")
    print(f"Approval Mode: {'AUTOMATED (--approve)' if auto_approve else 'INTERACTIVE'}")
    if product_index is not None:
        print(f"Selected Product Index: {product_index}")
    print("=" * 65)

    # Real Blinkit E2E uses Blinkit ONLY. Mock adapters are not in the graph.
    driver_manager = DriverManager(settings)
    blinkit_adapter = create_blinkit_appium_adapter(settings, driver_manager)
    adapters = [blinkit_adapter]

    intent_agent = get_intent_agent()
    rec_generator = get_recommendation_generator()

    graph = build_graph(intent_agent, adapters, rec_generator)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("\n[1] Executing Intent Understanding & Planning...")
    state = initial_state(query_text)
    paused = graph.invoke(state, config)

    # 1. Intent & Planning results
    intent = paused.get("intent")
    if intent and intent.products:
        prod_names = [p.name for p in intent.products]
        print(f"    [OK] Intent Understood: Products={prod_names}, Priority={intent.constraints.priority or 'best_value'}")
    else:
        print(f"    [!] Status: {paused.get('status')}")
        if paused.get("status") == "needs_clarification":
            print(f"    Clarification needed: {paused.get('error_message')}")
        return

    selected_stores = paused.get("selected_stores", [])
    print(f"    [OK] Stores Selected for Real E2E: {selected_stores}")

    # 2. Search & Extraction
    raw_results = paused.get("raw_results", [])
    blinkit_raw = [r for r in raw_results if r.store_id == "blinkit"]
    print(f"\n[2] REAL BLINKIT: Search Executed ({len(blinkit_raw)} raw items extracted from Blinkit UI):")
    for idx, r in enumerate(blinkit_raw[:7], 1):
        print(f"    [{idx}] {r.raw_title} | Price: {r.raw_price} | ETA: {r.raw_eta} | Qty: {r.raw_quantity}")

    # 3. Normalization & Relevant Candidate Ranking
    ranking = paused.get("ranking_summary")
    if not ranking or not ranking.rankings:
        print(f"\n[!] No relevant products found matching '{query_text}'. Status: {paused.get('status')}")
        return

    req_name = intent.products[0].name.lower()
    candidates = ranking.rankings.get(req_name) or ranking.rankings.get(intent.products[0].name) or next(iter(ranking.rankings.values()), [])
    if not candidates:
        print(f"\n[!] No relevant Blinkit candidates found for '{req_name}'.")
        return

    print(f"\n[3] REAL BLINKIT: Relevant Products for '{req_name}' ({len(candidates)} options):")
    for idx, rk in enumerate(candidates, 1):
        np = rk.product
        print(f"    [{idx}] {np.product_name} — ₹{np.price_inr:.2f} ({np.eta_minutes} mins)")

    if mode == "search":
        print("\n[SUCCESS] Search mode completed successfully. Stopping before product selection/order.")
        return

    # 4. Explicit Product Selection
    selected_idx = 0
    if product_index is not None:
        if 1 <= product_index <= len(candidates):
            selected_idx = product_index - 1
        else:
            print(f"\n[ERROR] Invalid product index {product_index}. Must be between 1 and {len(candidates)}.")
            sys.exit(1)
    elif auto_approve:
        print(
            f"\n[ERROR] When using --approve in add-to-cart/full mode, you must explicitly specify "
            f"which product to purchase via --product-index N (e.g. --product-index 1)."
        )
        sys.exit(1)
    else:
        # Interactive selection
        try:
            val = input(f"\nSelect a product (1-{len(candidates)}) [default: 1]: ").strip()
            if val:
                idx_val = int(val)
                if 1 <= idx_val <= len(candidates):
                    selected_idx = idx_val - 1
                else:
                    print(f"Invalid choice '{val}'. Defaulting to [1].")
                    selected_idx = 0
            else:
                selected_idx = 0
        except (ValueError, EOFError, KeyboardInterrupt):
            print("\nSelection cancelled.")
            sys.exit(1)

    chosen_candidate = candidates[selected_idx]
    chosen_product = chosen_candidate.product
    print(f"\n[4] Explicitly Selected Product [{selected_idx + 1}]:")
    print(f"    '{chosen_product.product_name}' — ₹{chosen_product.price_inr:.2f} (ETA: {chosen_product.eta_minutes} mins)")

    # Re-compute basket for single selected item
    chosen_basket = select_best_store(ranking, {req_name: selected_idx})
    if chosen_basket is None:
        print("\n[ERROR] Failed to construct basket for selected product.")
        sys.exit(1)

    rec = rec_generator.generate(chosen_basket, ranking.priority_used)
    graph.update_state(config, {"basket": chosen_basket, "recommendation": rec})

    # 5. Human Approval Flow
    print("\n[5] Human Approval Step:")
    if auto_approve:
        print(f"    [--approve with --product-index {selected_idx + 1}] Auto-approving order for '{chosen_product.product_name}'.")
        decision = "approved"
    else:
        try:
            resp = input(
                f"    Approve order from 'blinkit' for '{chosen_product.product_name}' (₹{chosen_basket.total_price_inr:.2f})? [Y/n]: "
            ).strip().lower()
            decision = "approved" if resp in ("", "y", "yes") else "rejected"
        except (EOFError, KeyboardInterrupt):
            print("\n    Interrupted. Cancelling.")
            decision = "rejected"

    if decision != "approved":
        print("    [CANCELLED] User rejected the recommendation.")
        final = graph.invoke(Command(resume={"decision": "rejected", "rejection_reason": "User declined"}), config)
        print(f"    Final Status: {final.get('status')}")
        return

    # 6. Order Execution (Add to Cart + Checkout)
    print("\n[6] Resuming LangGraph into Order Execution (Add to Cart & Checkout)...")
    final = graph.invoke(Command(resume={"decision": "approved"}), config)

    cart_results = final.get("cart_results", [])
    for cr in cart_results:
        status_str = "[OK]" if cr.success else "[FAILED]"
        msg_str = f" ({cr.message})" if not cr.success and cr.message else ""
        print(f"    [7] REAL BLINKIT: {status_str} Product added to cart: '{cr.product_name}' (Store: {cr.store_id}){msg_str}")

    checkout_state = final.get("checkout_state")
    if checkout_state:
        print(f"\n    [8] REAL BLINKIT: Checkout Navigation Status: '{checkout_state.status}'")
        print(f"        Message: {checkout_state.message}")

    final_status = final.get("status")
    print(f"\n    [9] Final Graph Status: '{final_status}'")
    if final_status == "ready_for_payment":
        print("=" * 65)
        print("[SUCCESS] WORKFLOW COMPLETE: Reached payment screen safely without confirming payment!")
        print("=" * 65)
    else:
        print(f"[!] Workflow ended in status: {final_status} ({final.get('error_message')})")


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-End LangGraph Shopping Agent with Real Blinkit Appium Adapter")
    parser.add_argument("--query", "-q", default="Dairy Milk Chocolate", help="User shopping prompt (default: 'Dairy Milk Chocolate')")
    parser.add_argument("--search", action="store_true", help="Execute search, ranking, and candidate display only")
    parser.add_argument("--add-to-cart", action="store_true", help="Execute search + product selection + add to cart")
    parser.add_argument("--checkout", "--full", action="store_true", dest="checkout", help="Execute full flow up to payment screen")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve recommendation without interactive prompt")
    parser.add_argument("--product-index", type=int, default=None, help="Explicit 1-based index of candidate product to select (required with --approve for ordering)")

    args = parser.parse_args()

    mode = "full"
    if args.search:
        mode = "search"
    elif args.add_to_cart:
        mode = "add_to_cart"
    elif args.checkout:
        mode = "full"

    run_e2e_blinkit(
        args.query,
        mode=mode,
        auto_approve=args.approve,
        product_index=args.product_index,
    )


if __name__ == "__main__":
    main()

