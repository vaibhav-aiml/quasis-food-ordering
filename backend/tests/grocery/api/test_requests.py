"""Tests for the ``/v1/requests`` endpoints — Phase 16: FastAPI
integration on top of Phase 15's real LangGraph workflow.

Same fixture pattern as ``tests/graph/test_workflow.py``: real Phase 7
mock store adapters (deterministic pricing, genuine add_to_cart/checkout
implementations), a stub intent agent (no real Ollama needed), and a
recommendation generator wired to a fake LLM client that deliberately
never validates — every scenario below either doesn't inspect
explanation text, or accepts the deterministic fallback as equally valid
proof the pipeline ran.

Each test builds its own app via ``create_app()`` and clears
``get_shopping_graph``'s cache first, so tests never share LangGraph
checkpoint state with each other despite the graph dependency being a
process-wide singleton by design (see ``get_shopping_graph``'s
docstring in ``app.core.dependencies`` for why that caching is
load-bearing, not incidental).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.core.dependencies as deps
from app.grocery.adapters.blinkit.adapter import BlinkitAdapter
from app.grocery.adapters.instamart.adapter import InstamartAdapter
from app.grocery.adapters.types import CheckoutState
from app.grocery.adapters.zepto.adapter import ZeptoAdapter
from app.grocery.agents.recommendation_agent import RecommendationGenerator
from app.core.config import Settings
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.shared.domain.constraints import Constraints, Priority
from app.grocery.domain.intent import IntentRequest
from app.grocery.domain.normalized_product import NormalizedProduct
from app.grocery.domain.product import ProductRequest
from app.grocery.domain.ranked_result import RankedResult
from app.main import create_app
from app.grocery.processing.ranking import RankingSummary


class _StubIntentAgent:
    def __init__(self, result: IntentRequest) -> None:
        self._result = result

    def extract(self, raw_text: str) -> IntentRequest:
        return self._result


class _FakeLLMClient:
    def chat(self, *, messages, response_format=None) -> str:
        return "not valid json"  # forces the deterministic fallback path


def _cheap_intent(raw_text: str = "I need onions, cheapest") -> IntentRequest:
    return IntentRequest(
        raw_text=raw_text,
        products=[ProductRequest(name="onion")],
        confidence=0.9,
        constraints=Constraints(priority=Priority.CHEAPEST, max_delivery_minutes=None, max_budget=None),
    )


def _vague_intent(raw_text: str = "get me something") -> IntentRequest:
    return IntentRequest(
        raw_text=raw_text,
        products=[],
        confidence=0.1,
        needs_clarification=True,
        clarification_reason="Too vague.",
    )


@pytest.fixture
def _wire_recommendation_generator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Swap in a deterministic RecommendationGenerator (fake LLM client
    that never validates, so every scenario exercises the safe fallback
    path — no real Ollama needed). ``monkeypatch`` guarantees the real
    ``get_recommendation_generator`` is restored after the test even if
    it raises, so other test modules in the same pytest session never
    see this fake leak into their own (separately cached) graph builds.
    """

    (tmp_path / "recommendation_explanation.txt").write_text(
        "Schema: $schema\nStore: $store_id\nPriority: $priority\nPrice: $total_price\n"
        "Eta: $max_eta\nProducts: $matched_products_list\n$missing_products_section",
        encoding="utf-8",
    )
    prompt_manager = PromptManager(templates_dir=tmp_path)
    service = StructuredLLMService(_FakeLLMClient(), prompt_manager, max_retries=0)

    deps.get_recommendation_generator.cache_clear()
    monkeypatch.setattr(deps, "get_recommendation_generator", lambda: RecommendationGenerator(service))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, _wire_recommendation_generator):
    """A fresh app + fresh graph (fresh in-memory checkpointer) per test.

    Patches ``get_intent_agent``/``get_all_store_adapters`` via
    ``monkeypatch`` (auto-restored at teardown) rather than raw
    reassignment, then clears ``get_shopping_graph``'s cache so the next
    call rebuilds a graph closing over these fakes. The cache is cleared
    again after the test (while the fakes are still active, before
    ``monkeypatch`` undoes them) so no test leaves a stub-built graph
    sitting in the process-wide cache for a later, unrelated test to
    pick up.
    """

    monkeypatch.setattr(deps, "get_intent_agent", lambda: _StubIntentAgent(_cheap_intent()))
    monkeypatch.setattr(
        deps,
        "get_all_store_adapters",
        lambda s=None: (ZeptoAdapter(), BlinkitAdapter(), InstamartAdapter()),
    )
    deps.get_shopping_graph.cache_clear()

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        app_name="Test Shopping Agent",
        app_version="0.0.0-test",
    )
    app = create_app(settings=settings)
    yield TestClient(app)
    deps.get_shopping_graph.cache_clear()


def _use_intent(monkeypatch: pytest.MonkeyPatch, intent: IntentRequest) -> None:
    monkeypatch.setattr(deps, "get_intent_agent", lambda: _StubIntentAgent(intent))
    deps.get_shopping_graph.cache_clear()


# --------------------------------------------------------------------------
# POST /v1/requests
# --------------------------------------------------------------------------


def test_create_request_returns_thread_id_and_pauses_for_approval(client: TestClient) -> None:
    response = client.post("/v1/requests", json={"raw_text": "I need onions, cheapest"})

    assert response.status_code == 201
    body = response.json()
    assert body["thread_id"]
    assert body["waiting_for_approval"] is True
    assert body["ready_for_payment"] is False
    assert body["recommendation"]["store_id"] == "zepto"  # cheapest in Phase 7 mock pricing
    assert "onion" in body["candidates"]
    assert body["order_confirmation"] is None


def test_create_request_never_auto_approves(client: TestClient) -> None:
    """The graph must stop on its own at awaiting_approval — nothing in
    the create path may submit an implicit decision.
    """

    response = client.post("/v1/requests", json={"raw_text": "I need onions"})
    body = response.json()

    assert body["status"] != "ready_for_payment"
    assert body["order_confirmation"] is None
    assert body["waiting_for_approval"] is True


def test_create_request_with_needs_clarification_never_pauses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_intent(monkeypatch, _vague_intent())
    response = client.post("/v1/requests", json={"raw_text": "get me something"})

    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["needs_clarification"] is True
    assert body["clarification_reason"] == "Too vague."
    assert body["waiting_for_approval"] is False


def test_create_request_rejects_blank_raw_text(client: TestClient) -> None:
    response = client.post("/v1/requests", json={"raw_text": ""})
    assert response.status_code == 422


# --------------------------------------------------------------------------
# GET /v1/requests/{thread_id}
# --------------------------------------------------------------------------


def test_get_request_returns_current_state(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.get(f"/v1/requests/{thread_id}")

    assert response.status_code == 200
    assert response.json()["thread_id"] == thread_id
    assert response.json()["waiting_for_approval"] is True


def test_get_unknown_thread_returns_404(client: TestClient) -> None:
    response = client.get("/v1/requests/does-not-exist")
    assert response.status_code == 404


# --------------------------------------------------------------------------
# POST /v1/requests/{thread_id}/approval
# --------------------------------------------------------------------------


def test_approval_resumes_the_thread_and_reaches_ready_for_payment(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_payment"
    assert body["ready_for_payment"] is True
    assert body["waiting_for_approval"] is False
    assert body["order_confirmation"]["store_id"] == "zepto"


def test_rejection_reaches_cancelled_and_never_ready_for_payment(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(
        f"/v1/requests/{thread_id}/approval",
        json={"decision": "rejected", "rejection_reason": "changed my mind"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["ready_for_payment"] is False


def test_approval_requires_explicit_decision_field(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(f"/v1/requests/{thread_id}/approval", json={})
    assert response.status_code == 422  # no implicit default decision exists


def test_modify_decision_without_modify_request_is_rejected(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "modify"})
    assert response.status_code == 422


def test_approval_on_unknown_thread_returns_404(client: TestClient) -> None:
    response = client.post("/v1/requests/does-not-exist/approval", json={"decision": "approved"})
    assert response.status_code == 404


def test_approval_on_already_completed_thread_returns_409(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]
    client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})

    response = client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})
    assert response.status_code == 409


def test_modify_with_satisfiable_change_loops_and_pauses_again(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(
        f"/v1/requests/{thread_id}/approval",
        json={"decision": "modify", "modify_request": {"updated_priority": "fastest"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["waiting_for_approval"] is True  # looped back through planning and paused again


def test_ready_for_payment_is_false_when_checkout_does_not_reach_payment_screen(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for the order_execution -> ready_for_payment edge
    bug: the graph must not report ready_for_payment when the real
    checkout flow failed to reach the payment screen.
    """

    class _FlakyZeptoAdapter(ZeptoAdapter):
        def checkout(self) -> CheckoutState:
            return CheckoutState(
                store_id="zepto", status="failed", message="Payment gateway timed out."
            )

    monkeypatch.setattr(
        deps,
        "get_all_store_adapters",
        lambda s=None: (_FlakyZeptoAdapter(), BlinkitAdapter(), InstamartAdapter()),
    )
    deps.get_shopping_graph.cache_clear()

    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]
    assert created["recommendation"]["store_id"] == "zepto"

    response = client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})

    body = response.json()
    assert body["status"] == "failed"
    assert body["ready_for_payment"] is False
    assert body["error_message"]


# --------------------------------------------------------------------------
# POST /v1/requests/{thread_id}/selection
# --------------------------------------------------------------------------


def test_selection_rejects_unknown_product_name(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(
        f"/v1/requests/{thread_id}/selection",
        json={"selected_indices": {"bananas": 0}},
    )
    assert response.status_code == 400


def test_selection_rejects_out_of_range_index(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]

    response = client.post(
        f"/v1/requests/{thread_id}/selection",
        json={"selected_indices": {"onion": 999}},
    )
    assert response.status_code == 400


def test_selection_on_unknown_thread_returns_404(client: TestClient) -> None:
    response = client.post(
        "/v1/requests/does-not-exist/selection",
        json={"selected_indices": {"onion": 0}},
    )
    assert response.status_code == 404


def test_selection_on_non_paused_thread_returns_409(client: TestClient) -> None:
    created = client.post("/v1/requests", json={"raw_text": "I need onions"}).json()
    thread_id = created["thread_id"]
    client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})

    response = client.post(
        f"/v1/requests/{thread_id}/selection",
        json={"selected_indices": {"onion": 0}},
    )
    assert response.status_code == 409


def test_selection_switches_the_candidate_used_within_the_recommended_store(
    client: TestClient,
) -> None:
    """Directly exercises select_best_store's real semantics: an index
    picks among the recommended STORE's OWN ranked candidates for a
    product (e.g. two listings from the same store), not which store
    wins overall. Injects a second same-store listing the way real
    Verification/Normalization/Ranking output would, since Phase 7's
    mock adapters only ever return one listing per store per product.
    """

    created = client.post("/v1/requests", json={"raw_text": "I need onions, cheapest"}).json()
    thread_id = created["thread_id"]
    assert created["recommendation"]["store_id"] == "zepto"

    graph = deps.get_shopping_graph()
    config = {"configurable": {"thread_id": thread_id}}

    loose = NormalizedProduct(
        store_id="zepto", product_name="onion", price_inr=10.0, eta_minutes=15, quantity=1.0, unit="unit"
    )
    one_kg = NormalizedProduct(
        store_id="zepto", product_name="onion", price_inr=11.0, eta_minutes=10, quantity=1.0, unit="kg"
    )
    instamart_listing = NormalizedProduct(
        store_id="instamart", product_name="onion", price_inr=12.5, eta_minutes=25, quantity=1.0, unit="unit"
    )
    ranking_summary = RankingSummary(
        rankings={
            "onion": [
                RankedResult(product=loose, rank=1, score=10.0, rationale="Cheapest option: Rs10.00"),
                RankedResult(product=one_kg, rank=2, score=11.0),
                RankedResult(product=instamart_listing, rank=3, score=12.5),
            ]
        },
        priority_used=Priority.CHEAPEST,
        excluded_counts={"onion": 0},
    )
    graph.update_state(config, {"ranking_summary": ranking_summary})

    # Still paused for approval after the direct state write.
    assert client.get(f"/v1/requests/{thread_id}").json()["waiting_for_approval"] is True

    response = client.post(
        f"/v1/requests/{thread_id}/selection",
        json={"selected_indices": {"onion": 1}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["waiting_for_approval"] is True
    assert body["selected_indices"] == {"onion": 1}
    rec = body["recommendation"]
    assert rec["store_id"] == "zepto"  # unchanged: zepto is still cheapest overall (11.0 < 12.5)
    matched = rec["basket"]["matched_products"][0]["product"]
    assert matched["price_inr"] == 11.0
    assert matched["unit"] == "kg"

    approval_response = client.post(f"/v1/requests/{thread_id}/approval", json={"decision": "approved"})
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "ready_for_payment"
    assert approval_response.json()["order_confirmation"]["store_id"] == "zepto"


def test_up_front_selected_indices_are_accepted_on_create(client: TestClient) -> None:
    """selected_indices may also be supplied on POST / itself, threaded
    through GraphState before recommendation_generation ever runs.
    """

    response = client.post(
        "/v1/requests",
        json={"raw_text": "I need onions", "selected_indices": {"onion": 0}},
    )

    assert response.status_code == 201
    assert response.json()["selected_indices"] == {"onion": 0}
