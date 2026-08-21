"""Integration tests for LangGraph workflow with Blinkit Appium Adapter.

Tests that the LangGraph pipeline seamlessly orchestrates with the Blinkit
adapter (both mock and Appium-backed fakes), verifying search routing, store
selection, product result propagation, add-to-cart, and checkout safety without
requiring a physical emulator or live Appium server.
"""

import uuid
from pathlib import Path

import pytest
from langgraph.types import Command

from app.adapters.base import StoreAdapter
from app.adapters.blinkit.adapter import BlinkitAdapter
from app.adapters.blinkit.appium_adapter import BlinkitAppiumAdapter
from app.adapters.instamart.adapter import InstamartAdapter
from app.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.adapters.zepto.adapter import ZeptoAdapter
from app.agents.recommendation_agent import RecommendationGenerator
from app.automation.driver_manager import DriverManager
from app.core.config import Settings
from app.core.dependencies import get_all_store_adapters
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.domain.constraints import Constraints, Priority
from app.domain.intent import IntentRequest
from app.domain.product import ProductRequest
from app.domain.raw_product_result import RawProductResult
from app.graph.state import initial_state
from app.graph.workflow import build_graph


class _StubIntentAgent:
    def __init__(self, result: IntentRequest) -> None:
        self._result = result

    def extract(self, raw_text: str) -> IntentRequest:
        return self._result


class _FakeLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, *, messages, response_format=None) -> str:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


class _TrackedBlinkitAdapter:
    """Tracked adapter simulating BlinkitAppiumAdapter's interface and operations."""

    def __init__(
        self,
        results: list[RawProductResult] | None = None,
        cart_success: bool = True,
        checkout_status: str = "ready_for_payment",
    ) -> None:
        self._store_id = "blinkit"
        self._results = results or [
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Chocolate Bar",
                raw_price="₹175",
                raw_eta="12 mins",
                raw_quantity="150 g",
            )
        ]
        self._cart_success = cart_success
        self._checkout_status = checkout_status
        self.search_called_with: list[SearchQuery] = []
        self.add_to_cart_called_with: list[RawProductResult] = []
        self.checkout_called_count: int = 0

    def get_store_id(self) -> str:
        return self._store_id

    def is_available(self) -> bool:
        return True

    def _ensure_session(self) -> None:
        pass

    def search(self, query: SearchQuery) -> list[RawProductResult]:
        self.search_called_with.append(query)
        return self._results

    def add_to_cart(self, product: RawProductResult) -> CartActionResult:
        self.add_to_cart_called_with.append(product)
        return CartActionResult(
            store_id=self._store_id,
            product_name=product.raw_title,
            success=self._cart_success,
        )

    def checkout(self) -> CheckoutState:
        self.checkout_called_count += 1
        return CheckoutState(
            store_id=self._store_id,
            status=self._checkout_status,
            message="Reached the payment screen. Payment was NOT confirmed — stopping here by design.",
        )


@pytest.fixture
def recommendation_generator(tmp_path: Path) -> RecommendationGenerator:
    (tmp_path / "recommendation_explanation.txt").write_text(
        "Schema: $schema\nStore: $store_id\nPriority: $priority\nPrice: $total_price\n"
        "Eta: $max_eta\nProducts: $matched_products_list\n$missing_products_section",
        encoding="utf-8",
    )
    prompt_manager = PromptManager(templates_dir=tmp_path)
    client = _FakeLLMClient(["not valid json"] * 10)
    return RecommendationGenerator(StructuredLLMService(client, prompt_manager, max_retries=0))


def _fresh_config() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _dairy_milk_intent(raw_text: str = "Find Dairy Milk Chocolate on Blinkit") -> IntentRequest:
    return IntentRequest(
        raw_text=raw_text,
        products=[ProductRequest(name="Dairy Milk Chocolate")],
        confidence=0.95,
        constraints=Constraints(priority=Priority.BEST_VALUE),
    )


# --- Test 1: Blinkit search routing -------------------------------------------


def test_langgraph_routes_search_to_blinkit_adapter(recommendation_generator) -> None:
    """Verify: User request -> LangGraph -> Blinkit adapter -> search."""

    tracked_blinkit = _TrackedBlinkitAdapter()
    adapters: list[StoreAdapter] = [ZeptoAdapter(), tracked_blinkit, InstamartAdapter()]

    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        adapters,
        recommendation_generator,
    )
    config = _fresh_config()

    paused = graph.invoke(initial_state("Find Dairy Milk Chocolate on Blinkit"), config)

    assert len(tracked_blinkit.search_called_with) == 1
    assert tracked_blinkit.search_called_with[0].products[0].name.lower() == "dairy milk chocolate"
    assert "__interrupt__" in paused


# --- Test 2: Real adapter selection -------------------------------------------


def test_real_adapter_selection_selects_blinkit_appium_and_mocks_others() -> None:
    """Verify: BLINKIT_STORE_MODE=real gives BlinkitAppiumAdapter, while Zepto and Instamart are mocks."""

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        store_mode="mock",
        blinkit_store_mode="real",
        zepto_store_mode="mock",
        instamart_store_mode="mock",
    )

    adapters = get_all_store_adapters(settings)
    adapters_by_id = {a.get_store_id(): a for a in adapters}

    assert isinstance(adapters_by_id["blinkit"], BlinkitAppiumAdapter)
    assert isinstance(adapters_by_id["zepto"], ZeptoAdapter)
    assert isinstance(adapters_by_id["instamart"], InstamartAdapter)


def test_default_settings_selects_all_mock_adapters() -> None:
    """Verify: Default settings gives all mock adapters for fast/offline execution."""

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    adapters = get_all_store_adapters(settings)
    adapters_by_id = {a.get_store_id(): a for a in adapters}

    assert isinstance(adapters_by_id["blinkit"], BlinkitAdapter)
    assert isinstance(adapters_by_id["zepto"], ZeptoAdapter)
    assert isinstance(adapters_by_id["instamart"], InstamartAdapter)


# --- Test 3: Product result propagation ---------------------------------------


def test_product_result_propagation_from_blinkit_to_recommendation(
    recommendation_generator,
) -> None:
    """Verify: Raw products from Blinkit flow through Verification -> Normalization -> Ranking -> Recommendation."""

    tracked_blinkit = _TrackedBlinkitAdapter(
        results=[
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Chocolate Bar",
                raw_price="₹175",
                raw_eta="10 mins",
                raw_quantity="150 g",
            )
        ]
    )

    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        [tracked_blinkit],
        recommendation_generator,
    )
    config = _fresh_config()

    paused = graph.invoke(initial_state("Find Dairy Milk Chocolate on Blinkit"), config)

    assert "__interrupt__" in paused
    assert paused["verification_result"] is not None
    assert len(paused["normalized_products"]) == 1
    norm = paused["normalized_products"][0]
    assert norm.store_id == "blinkit"
    assert norm.price_inr == 175.0
    assert norm.eta_minutes == 10
    assert norm.unit == "g"

    assert paused["ranking_summary"] is not None
    assert paused["basket"] is not None
    assert paused["basket"].store_id == "blinkit"
    assert paused["recommendation"] is not None
    assert paused["recommendation"].store_id == "blinkit"


# --- Test 4: Add-to-cart routing ----------------------------------------------


def test_approval_outcome_routes_to_blinkit_add_to_cart(
    recommendation_generator,
) -> None:
    """Verify: Approving recommendation calls Blinkit adapter's add_to_cart."""

    tracked_blinkit = _TrackedBlinkitAdapter()
    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        [tracked_blinkit],
        recommendation_generator,
    )
    config = _fresh_config()

    graph.invoke(initial_state("Find Dairy Milk Chocolate on Blinkit"), config)
    final = graph.invoke(Command(resume={"decision": "approved"}), config)

    assert len(tracked_blinkit.add_to_cart_called_with) == 1
    added_prod = tracked_blinkit.add_to_cart_called_with[0]
    assert "cadbury dairy milk silk" in added_prod.raw_title.lower()
    assert final["cart_results"][0].success is True


# --- Test 5: Checkout safety --------------------------------------------------


def test_checkout_terminates_at_ready_for_payment_safely(
    recommendation_generator,
) -> None:
    """Verify: Checkout reaches payment screen, sets ready_for_payment, and stops safely."""

    tracked_blinkit = _TrackedBlinkitAdapter()
    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        [tracked_blinkit],
        recommendation_generator,
    )
    config = _fresh_config()

    graph.invoke(initial_state("Find Dairy Milk Chocolate on Blinkit"), config)
    final = graph.invoke(Command(resume={"decision": "approved"}), config)

    assert tracked_blinkit.checkout_called_count == 1
    assert final["status"] == "ready_for_payment"
    assert final["checkout_state"].status == "ready_for_payment"
    assert "NOT confirmed" in final["checkout_state"].message
    assert final["order_confirmation"]["store_id"] == "blinkit"


# --- Test 6: Irrelevant product filtering & single item basket ----------------


def test_irrelevant_search_results_filtered_and_candidate_grouped(
    recommendation_generator,
) -> None:
    """Verify: Unrelated products (e.g. rice) are filtered out, and only relevant items are ranked."""

    tracked_blinkit = _TrackedBlinkitAdapter(
        results=[
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Desserts Brownie Milk Chocolate Bar",
                raw_price="₹207",
                raw_eta="12 mins",
                raw_quantity="140 g",
            ),
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Oreo Milk Chocolate Bar",
                raw_price="₹100",
                raw_eta="12 mins",
                raw_quantity="58.5 g",
            ),
            RawProductResult(
                store_id="blinkit",
                raw_title="Whole Farm Premium Parmal Rice",
                raw_price="₹55",
                raw_eta="12 mins",
                raw_quantity="1 kg",
            ),
        ]
    )

    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        [tracked_blinkit],
        recommendation_generator,
    )
    config = _fresh_config()

    paused = graph.invoke(initial_state("Dairy Milk Chocolate"), config)

    ranking = paused["ranking_summary"]
    assert "dairy milk chocolate" in ranking.rankings
    ranked_candidates = ranking.rankings["dairy milk chocolate"]
    # Both chocolate variants are included, but rice is excluded
    assert len(ranked_candidates) == 2
    for r in ranked_candidates:
        assert "dairy milk" in r.product.product_name

    # Basket has exactly 1 selected product (the top rank #1)
    basket = paused["basket"]
    assert len(basket.matched_products) == 1
    assert basket.matched_products[0].product.product_name == "cadbury dairy milk silk oreo milk chocolate bar"


# --- Test 7: Explicit candidate selection and single item add-to-cart ---------


def test_explicit_candidate_selection_adds_only_selected_product(
    recommendation_generator,
) -> None:
    """Verify: Selecting a specific candidate index updates basket to only add that 1 item to cart."""

    tracked_blinkit = _TrackedBlinkitAdapter(
        results=[
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Desserts Brownie Milk Chocolate Bar",
                raw_price="₹207",
                raw_eta="12 mins",
                raw_quantity="140 g",
            ),
            RawProductResult(
                store_id="blinkit",
                raw_title="Cadbury Dairy Milk Silk Oreo Milk Chocolate Bar",
                raw_price="₹100",
                raw_eta="12 mins",
                raw_quantity="58.5 g",
            ),
        ]
    )

    graph = build_graph(
        _StubIntentAgent(_dairy_milk_intent()),
        [tracked_blinkit],
        recommendation_generator,
    )
    config = _fresh_config()

    paused = graph.invoke(initial_state("Dairy Milk Chocolate"), config)

    # Select candidate index 1 (Brownie bar at ₹207)
    from app.processing.recommendation_selection import select_best_store
    chosen_basket = select_best_store(paused["ranking_summary"], {"dairy milk chocolate": 1})
    assert chosen_basket is not None
    assert len(chosen_basket.matched_products) == 1
    assert chosen_basket.matched_products[0].product.product_name == "cadbury dairy milk silk desserts brownie milk chocolate bar"

    # Update graph state with chosen basket
    graph.update_state(config, {"basket": chosen_basket})

    final = graph.invoke(Command(resume={"decision": "approved"}), config)

    # Only 1 item added to cart
    assert len(tracked_blinkit.add_to_cart_called_with) == 1
    assert "desserts brownie" in tracked_blinkit.add_to_cart_called_with[0].raw_title.lower()
    assert final["status"] == "ready_for_payment"

