"""End-to-end tests for the compiled graph (app.grocery.graph.workflow.build_graph)
— Phase 15: the real graph, real adapters (Phase 7's mocks — deterministic,
no device needed), real Verification/Normalization/Ranking/Recommendation-
selection logic. Only the intent agent's LLM and the recommendation
explanation's LLM are faked, exactly as in every previous phase's tests.

IMPORTANT: requires the real `langgraph` package (a project dependency)
and could not be executed in the offline sandbox that built this phase —
every individual node's logic was verified there (see Phase 15 docs);
this file is what actually proves the WIRING is correct, and needs to be
run for real.
"""

import uuid
from pathlib import Path

import pytest
from langgraph.types import Command

from app.grocery.adapters.blinkit.adapter import BlinkitAdapter
from app.grocery.adapters.instamart.adapter import InstamartAdapter
from app.grocery.adapters.zepto.adapter import ZeptoAdapter
from app.grocery.agents.recommendation_agent import RecommendationGenerator
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.shared.domain.constraints import Constraints, Priority
from app.grocery.domain.intent import IntentRequest
from app.grocery.domain.product import ProductRequest
from app.grocery.graph.state import initial_state
from app.grocery.graph.workflow import build_graph


class _StubIntentAgent:
    """Deterministic, no LLM — same pattern as Phase 5's tests."""

    def __init__(self, result: IntentRequest) -> None:
        self._result = result

    def extract(self, raw_text: str) -> IntentRequest:
        return self._result


class _FakeLLMClient:
    """Same pattern as Phase 3/4/12's tests."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, *, messages, response_format=None) -> str:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


@pytest.fixture
def real_mock_adapters():
    """Phase 7's real (mock-data) adapters — deterministic pricing,
    genuinely implement add_to_cart/checkout (unlike Phase 8's Appium
    adapters, which need real locators this repo doesn't have yet).
    """

    return [ZeptoAdapter(), BlinkitAdapter(), InstamartAdapter()]


@pytest.fixture
def recommendation_generator(tmp_path: Path) -> RecommendationGenerator:
    (tmp_path / "recommendation_explanation.txt").write_text(
        "Schema: $schema\nStore: $store_id\nPriority: $priority\nPrice: $total_price\n"
        "Eta: $max_eta\nProducts: $matched_products_list\n$missing_products_section",
        encoding="utf-8",
    )
    prompt_manager = PromptManager(templates_dir=tmp_path)
    # Deliberately scripted to never validate — every scenario below either
    # doesn't inspect explanation text, or accepts the deterministic
    # fallback (used_fallback=True) as equally valid proof the pipeline ran.
    client = _FakeLLMClient(["not valid json"] * 10)
    return RecommendationGenerator(StructuredLLMService(client, prompt_manager, max_retries=0))


def _fresh_config() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _cheap_intent(raw_text: str = "I need onions, cheapest") -> IntentRequest:
    return IntentRequest(
        raw_text=raw_text,
        products=[ProductRequest(name="onion")],
        confidence=0.9,
        constraints=Constraints(priority=Priority.CHEAPEST, max_delivery_minutes=None, max_budget=None),
    )


def test_full_happy_path_reaches_ready_for_payment(real_mock_adapters, recommendation_generator) -> None:
    graph = build_graph(_StubIntentAgent(_cheap_intent()), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    paused = graph.invoke(initial_state("I need onions, cheapest"), config)

    assert "__interrupt__" in paused
    interrupt_payload = paused["__interrupt__"][0].value
    assert interrupt_payload["store_id"] == "zepto"  # Zepto is cheapest in Phase 7's mock pricing

    final = graph.invoke(Command(resume={"decision": "approved"}), config)

    assert "__interrupt__" not in final
    assert final["status"] == "ready_for_payment"
    assert final["order_confirmation"]["store_id"] == "zepto"
    assert final["cart_results"][0].success is True


def test_rejection_path_ends_in_cancelled(real_mock_adapters, recommendation_generator) -> None:
    graph = build_graph(_StubIntentAgent(_cheap_intent()), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    graph.invoke(initial_state("I need onions"), config)
    final = graph.invoke(Command(resume={"decision": "rejected"}), config)

    assert final["status"] == "cancelled"


def test_modify_with_excluding_budget_yields_failed_not_a_second_pause(
    real_mock_adapters, recommendation_generator
) -> None:
    """A budget of 5 excludes every mock store's price (cheapest is 10)
    — proves the modified constraint actually took effect on re-ranking,
    and that an unsatisfiable modify correctly reaches 'failed' rather
    than pausing for approval on nothing.
    """

    graph = build_graph(_StubIntentAgent(_cheap_intent()), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    first = graph.invoke(initial_state("I need onions"), config)
    assert "__interrupt__" in first

    second = graph.invoke(
        Command(resume={"decision": "modify", "modify_request": {"updated_max_budget": 5.0}}),
        config,
    )

    assert "__interrupt__" not in second
    assert second["status"] == "failed"


def test_modify_with_satisfiable_change_loops_through_planning_and_pauses_again(
    real_mock_adapters, recommendation_generator
) -> None:
    """A modify that STILL leaves a viable store (switching priority to
    fastest, rather than excluding everyone) proves the
    modify -> planning -> ... -> awaiting_approval cycle is a genuine,
    working loop, not a dead end.
    """

    graph = build_graph(_StubIntentAgent(_cheap_intent()), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    first = graph.invoke(initial_state("I need onions"), config)
    assert "__interrupt__" in first

    second = graph.invoke(
        Command(resume={"decision": "modify", "modify_request": {"updated_priority": "fastest"}}),
        config,
    )
    assert "__interrupt__" in second  # looped all the way back and paused again

    final = graph.invoke(Command(resume={"decision": "approved"}), config)
    assert final["status"] == "ready_for_payment"


def test_modify_raw_text_loops_back_through_intent_understanding(
    real_mock_adapters, recommendation_generator
) -> None:
    call_log: list[str] = []

    class _TrackingStubAgent:
        def extract(self, raw_text: str) -> IntentRequest:
            call_log.append(raw_text)
            return _cheap_intent(raw_text)

    graph = build_graph(_TrackingStubAgent(), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    graph.invoke(initial_state("I need onions"), config)
    graph.invoke(
        Command(
            resume={
                "decision": "modify",
                "modify_request": {"updated_raw_text": "actually I need curd"},
            }
        ),
        config,
    )

    assert "actually I need curd" in call_log  # intent_understanding was re-run


def test_needs_clarification_never_pauses(real_mock_adapters, recommendation_generator) -> None:
    vague_intent = IntentRequest(
        raw_text="get me something",
        products=[],
        confidence=0.1,
        needs_clarification=True,
        clarification_reason="Too vague.",
    )
    graph = build_graph(_StubIntentAgent(vague_intent), real_mock_adapters, recommendation_generator)
    config = _fresh_config()

    result = graph.invoke(initial_state("get me something"), config)

    assert "__interrupt__" not in result
    assert result["status"] == "needs_clarification"


def test_no_results_found_skips_approval_entirely(recommendation_generator) -> None:
    """An impossibly low budget forces zero valid results through
    Ranking, so no store can be recommended at all.
    """

    intent = IntentRequest(
        raw_text="I need onions, budget 1 rupee",
        products=[ProductRequest(name="onion")],
        confidence=0.9,
        constraints=Constraints(priority=None, max_delivery_minutes=None, max_budget=1.0),
    )
    graph = build_graph(
        _StubIntentAgent(intent),
        [ZeptoAdapter(), BlinkitAdapter(), InstamartAdapter()],
        recommendation_generator,
    )
    config = _fresh_config()

    result = graph.invoke(initial_state("I need onions, budget 1 rupee"), config)

    assert "__interrupt__" not in result  # never reached awaiting_approval
    assert result["status"] == "failed"
