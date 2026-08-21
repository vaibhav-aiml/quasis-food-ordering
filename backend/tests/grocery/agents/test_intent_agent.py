"""Tests for app.grocery.agents.intent_agent.

Four levels of testing:

1. ``_looks_obviously_vague`` (pre-LLM short-circuit) -- no LLM at all.
2. Other pure logic functions (merge, filter, sanitize, policy) -- no LLM.
3. IntentUnderstandingAgent.extract() end-to-end through a real
   StructuredLLMService, backed by a FakeLLMClient -- no real Ollama
   server needed, while still exercising render -> call -> parse ->
   validate -> sanitize -> policy.
4. Five required scenarios from the Phase 4 anti-hallucination fix.

The three vague-request scenarios ("get me something for dinner", "I need
food", "buy something") are now caught by the pre-LLM short-circuit and
never reach the LLM at all -- verified explicitly via a FakeLLMClient with
zero scripted responses, which would raise if called even once. This is a
stronger guarantee than the earlier post-hoc sanitization alone: the model
never gets a chance to hallucinate for these cases, because it's never
asked. Post-hoc sanitization (tested separately below) remains the
backstop for cases that DO reach the LLM but turn out ambiguous anyway.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.grocery.agents.intent_agent import (
    IntentUnderstandingAgent,
    _ExtractedConstraints,
    _ExtractedPriority,
    _enforce_extraction_policy,
    _filter_unsupported_products,
    _looks_obviously_vague,
    _sanitize_constraints,
    _sanitize_product_quantities,
    _to_domain_constraints,
    merge_duplicate_products,
)
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.shared.domain.constraints import Priority
from app.grocery.domain.product import ProductRequest


# --- _looks_obviously_vague: the pre-LLM short-circuit ----------------------


@pytest.mark.parametrize(
    "raw_text",
    [
        "get me something for dinner",
        "I need food",
        "buy something",
        "I want some food please",
        "get me some snacks",
    ],
)
def test_looks_obviously_vague_detects_filler_only_requests(raw_text: str) -> None:
    assert _looks_obviously_vague(raw_text) is True


@pytest.mark.parametrize(
    "raw_text",
    [
        "I am making biryani. I need onions and curd. Find the cheapest "
        "option that can deliver within 20 minutes.",
        "I need onions",
        "Order 2kg onions urgently",
        "I need milk",
        "get me onions for dinner",  # has "dinner" but also a real product
        "buy chicken",
    ],
)
def test_looks_obviously_vague_returns_false_when_product_noun_present(
    raw_text: str,
) -> None:
    assert _looks_obviously_vague(raw_text) is False


# --- merge_duplicate_products: pure logic, no LLM ---------------------------


def test_merge_sums_quantities_for_same_name_and_unit() -> None:
    products = [
        ProductRequest(name="onion", quantity=2, unit="kg"),
        ProductRequest(name="onion", quantity=1, unit="kg"),
    ]
    result = merge_duplicate_products(products)
    assert len(result) == 1
    assert result[0].quantity == 3


def test_merge_keeps_separate_entries_for_different_units() -> None:
    products = [
        ProductRequest(name="onion", quantity=2, unit="kg"),
        ProductRequest(name="onion", quantity=1, unit="unit"),
    ]
    assert len(merge_duplicate_products(products)) == 2


def test_merge_handles_empty_list() -> None:
    assert merge_duplicate_products([]) == []


# --- _filter_unsupported_products: the anti-hallucination product check ----


def test_filter_rejects_products_not_present_in_raw_text() -> None:
    raw_text = "get me something for dinner"
    hallucinated = [
        ProductRequest(name="chicken"),
        ProductRequest(name="rice"),
        ProductRequest(name="vegetables"),
    ]

    supported, rejected = _filter_unsupported_products(hallucinated, raw_text)

    assert supported == []
    assert set(rejected) == {"chicken", "rice", "vegetables"}


def test_filter_keeps_products_present_in_raw_text() -> None:
    raw_text = "I am making biryani. I need onions and curd."
    legit = [ProductRequest(name="onion"), ProductRequest(name="curd")]

    supported, rejected = _filter_unsupported_products(legit, raw_text)

    assert [p.name for p in supported] == ["onion", "curd"]
    assert rejected == []


def test_filter_is_case_insensitive() -> None:
    raw_text = "I need ONIONS please"
    supported, rejected = _filter_unsupported_products(
        [ProductRequest(name="onion")], raw_text
    )
    assert [p.name for p in supported] == ["onion"]
    assert rejected == []


# --- _sanitize_product_quantities: anti-hallucination quantity check -------


def test_sanitize_quantities_resets_when_raw_text_has_no_digits() -> None:
    raw_text = "get me something for dinner"
    products = [ProductRequest(name="chicken", quantity=3, unit="kg")]

    result = _sanitize_product_quantities(products, raw_text)

    assert result[0].quantity == 1.0
    assert result[0].unit == "unit"


def test_sanitize_quantities_preserves_when_raw_text_has_digits() -> None:
    raw_text = "Order 2kg onions"
    products = [ProductRequest(name="onion", quantity=2, unit="kg")]

    result = _sanitize_product_quantities(products, raw_text)

    assert result[0].quantity == 2.0
    assert result[0].unit == "kg"


# --- _sanitize_constraints: anti-hallucination constraint check ------------


def test_sanitize_constraints_zeroes_when_raw_text_has_no_digits() -> None:
    raw_text = "get me something for dinner"
    hallucinated = _ExtractedConstraints(
        max_delivery_minutes=60, priority=_ExtractedPriority.BEST_VALUE, max_budget=500.0
    )

    result = _sanitize_constraints(hallucinated, raw_text)

    assert result.max_delivery_minutes == 0
    assert result.max_budget == 0


def test_sanitize_constraints_preserves_when_raw_text_has_digits() -> None:
    raw_text = "deliver within 20 minutes"
    legit = _ExtractedConstraints(
        max_delivery_minutes=20, priority=_ExtractedPriority.CHEAPEST, max_budget=0
    )

    result = _sanitize_constraints(legit, raw_text)

    assert result.max_delivery_minutes == 20


# --- _to_domain_constraints: sentinel -> None mapping -----------------------


def test_to_domain_constraints_maps_sentinel_zero_to_none() -> None:
    extracted = _ExtractedConstraints(
        max_delivery_minutes=0, priority=_ExtractedPriority.BEST_VALUE, max_budget=0
    )
    result = _to_domain_constraints(extracted)
    assert result.max_delivery_minutes is None
    assert result.max_budget is None


def test_to_domain_constraints_preserves_nonzero_values() -> None:
    extracted = _ExtractedConstraints(
        max_delivery_minutes=20, priority=_ExtractedPriority.FASTEST, max_budget=200.0
    )
    result = _to_domain_constraints(extracted)
    assert result.max_delivery_minutes == 20
    assert result.max_budget == 200.0
    assert result.priority == Priority.FASTEST


def test_to_domain_constraints_maps_unspecified_priority_to_none() -> None:
    """Regression test for the deferred priority fix: 'unspecified' (the
    LLM-facing sentinel) must map to domain priority=None, not
    Priority.BEST_VALUE -- defaulting is the Ranking Engine's job
    (Phase 11), not the extraction layer's.
    """

    extracted = _ExtractedConstraints(
        max_delivery_minutes=0, priority=_ExtractedPriority.UNSPECIFIED, max_budget=0
    )
    result = _to_domain_constraints(extracted)
    assert result.priority is None


def test_extracted_constraints_priority_field_is_required_and_non_nullable() -> None:
    """Guards the deferred-fix decision: priority stays required and
    non-nullable at the LLM-facing schema level (Incident-1 lesson) even
    though it now supports "not stated" -- via a 4th enum value
    (UNSPECIFIED), never via making the field itself Optional/nullable.
    """

    schema = _ExtractedConstraints.model_json_schema()
    assert "priority" in schema.get("required", [])
    field_schema = schema["properties"]["priority"]
    assert "anyOf" not in field_schema


# --- _enforce_extraction_policy: the final deterministic decision ----------


def test_policy_forces_clarification_when_products_empty() -> None:
    needs_clarification, reason, confidence = _enforce_extraction_policy(
        products=[],
        llm_needs_clarification=False,
        llm_clarification_reason="",
        llm_confidence=0.8,
    )
    assert needs_clarification is True
    assert confidence <= 0.5
    assert reason


def test_policy_forces_clarification_on_low_confidence_even_with_products() -> None:
    needs_clarification, reason, confidence = _enforce_extraction_policy(
        products=[ProductRequest(name="onion")],
        llm_needs_clarification=False,
        llm_clarification_reason="",
        llm_confidence=0.3,
    )
    assert needs_clarification is True
    assert confidence <= 0.5


def test_policy_respects_confident_llm_with_products() -> None:
    needs_clarification, reason, confidence = _enforce_extraction_policy(
        products=[ProductRequest(name="onion")],
        llm_needs_clarification=False,
        llm_clarification_reason="",
        llm_confidence=0.9,
    )
    assert needs_clarification is False
    assert reason is None
    assert confidence == 0.9


def test_policy_never_leaves_reason_blank_when_clarification_needed() -> None:
    _, reason, _ = _enforce_extraction_policy(
        products=[],
        llm_needs_clarification=True,
        llm_clarification_reason="",  # LLM gave no reason at all
        llm_confidence=0.1,
    )
    assert reason  # falls back to DEFAULT_CLARIFICATION_REASON, never empty


# --- IntentUnderstandingAgent.extract(): end-to-end with a fake client ------


class FakeLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append({"messages": messages, "response_format": response_format})
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


@pytest.fixture
def prompt_manager(tmp_path: Path) -> PromptManager:
    (tmp_path / "intent_extraction.txt").write_text(
        "Schema: $schema\nRequest: $user_message", encoding="utf-8"
    )
    return PromptManager(templates_dir=tmp_path)


def _agent_with_responses(
    responses: list[str], prompt_manager: PromptManager
) -> tuple[IntentUnderstandingAgent, FakeLLMClient]:
    client = FakeLLMClient(responses)
    service = StructuredLLMService(client, prompt_manager)
    return IntentUnderstandingAgent(service), client


# ============================================================================
# Required scenario tests (Phase 4 anti-hallucination fix)
# ============================================================================


def test_scenario_vague_dinner_request_never_calls_llm(
    prompt_manager: PromptManager,
) -> None:
    """'get me something for dinner' -- the pre-LLM short-circuit must
    catch this BEFORE any LLM call. Uses zero scripted responses:
    FakeLLMClient raises if .chat() is invoked even once, so this test
    fails loudly if the short-circuit regresses.
    """

    raw_text = "get me something for dinner"
    agent, client = _agent_with_responses([], prompt_manager)

    result = agent.extract(raw_text)

    assert len(client.calls) == 0, "LLM must not be called for an obviously vague request"
    assert result.products == []
    assert result.constraints.max_delivery_minutes is None
    assert result.constraints.max_budget is None
    assert result.needs_clarification is True
    assert result.clarification_reason
    assert result.confidence <= 0.5


def test_scenario_i_need_food_never_calls_llm(prompt_manager: PromptManager) -> None:
    """'I need food' -- same pre-LLM short-circuit, different wording."""

    raw_text = "I need food"
    agent, client = _agent_with_responses([], prompt_manager)

    result = agent.extract(raw_text)

    assert len(client.calls) == 0
    assert result.products == []
    assert result.needs_clarification is True
    assert result.confidence <= 0.5


def test_scenario_buy_something_never_calls_llm(prompt_manager: PromptManager) -> None:
    """'buy something' -- no product noun at all; short-circuited too."""

    raw_text = "buy something"
    agent, client = _agent_with_responses([], prompt_manager)

    result = agent.extract(raw_text)

    assert len(client.calls) == 0
    assert result.products == []
    assert result.needs_clarification is True
    assert result.confidence <= 0.5


def test_scenario_vague_request_with_a_real_product_still_reaches_llm_and_is_sanitized(
    prompt_manager: PromptManager,
) -> None:
    """A request that mentions dinner AND a real product noun should NOT
    be short-circuited (it has extractable content) -- but if the LLM
    still hallucinates extra products beyond what's stated, the post-LLM
    sanitization layer (tested separately above) remains the backstop.
    This test confirms the two layers compose correctly: short-circuit
    skips only the truly empty cases; everything else still gets the full
    post-LLM safety net.
    """

    raw_text = "get me onions for dinner"
    hallucinating_llm_output = json.dumps(
        {
            "products": [
                {"name": "onion"},
                {"name": "chicken"},  # hallucinated -- not in raw text
            ],
            "constraints": {
                "max_delivery_minutes": 45,  # hallucinated -- no digits in raw text
                "priority": "unspecified",
                "max_budget": 0,
            },
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.7,
        }
    )
    agent, client = _agent_with_responses([hallucinating_llm_output], prompt_manager)

    result = agent.extract(raw_text)

    assert len(client.calls) == 1  # reached the LLM, since "onion" is a real noun
    assert {p.name for p in result.products} == {"onion"}  # chicken rejected
    assert result.constraints.max_delivery_minutes is None  # 45 zeroed, no digits stated


def test_scenario_valid_explicit_request_is_not_over_sanitized(
    prompt_manager: PromptManager,
) -> None:
    """The canonical biryani request -- a well-behaved LLM output should
    pass through with products and constraints intact, no false-positive
    clarification triggered.
    """

    raw_text = (
        "I am making biryani. I need onions and curd. Find the cheapest "
        "option that can deliver within 20 minutes."
    )
    llm_output = json.dumps(
        {
            "products": [{"name": "onion"}, {"name": "curd"}],
            "constraints": {
                "max_delivery_minutes": 20,
                "priority": "cheapest",
                "max_budget": 0,
            },
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.9,
        }
    )
    agent, _ = _agent_with_responses([llm_output], prompt_manager)

    result = agent.extract(raw_text)

    assert {p.name for p in result.products} == {"onion", "curd"}
    assert result.constraints.max_delivery_minutes == 20
    assert result.constraints.priority.value == "cheapest"
    assert result.needs_clarification is False
    assert result.clarification_reason is None
    assert result.confidence == 0.9


def test_scenario_explicit_constraints_request_preserved(
    prompt_manager: PromptManager,
) -> None:
    """A request with explicit budget AND delivery time -- both must
    survive sanitization since digits are genuinely present in the text.
    """

    raw_text = (
        "I need onions and curd, deliver within 20 minutes, budget 300 rupees."
    )
    llm_output = json.dumps(
        {
            "products": [{"name": "onion"}, {"name": "curd"}],
            "constraints": {
                "max_delivery_minutes": 20,
                "priority": "unspecified",
                "max_budget": 300.0,
            },
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.85,
        }
    )
    agent, _ = _agent_with_responses([llm_output], prompt_manager)

    result = agent.extract(raw_text)

    assert result.constraints.max_delivery_minutes == 20
    assert result.constraints.max_budget == 300.0
    assert result.constraints.priority is None  # no priority wording stated
    assert result.needs_clarification is False


# --- Existing coverage retained: raw_text handling, retries, empty input ---


def test_extract_sets_raw_text_from_python_not_llm(prompt_manager: PromptManager) -> None:
    llm_output = json.dumps(
        {
            "products": [{"name": "Onion"}],
            "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0},
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.95,
        }
    )
    agent, client = _agent_with_responses([llm_output], prompt_manager)

    result = agent.extract("I am making biryani, need onions")

    assert result.raw_text == "I am making biryani, need onions"
    assert len(client.calls) == 1


def test_extract_empty_raw_text_raises_without_calling_llm(prompt_manager: PromptManager) -> None:
    agent, client = _agent_with_responses([], prompt_manager)

    with pytest.raises(ValueError):
        agent.extract("   ")

    assert len(client.calls) == 0


def test_extract_recovers_from_one_invalid_llm_response(prompt_manager: PromptManager) -> None:
    bad = "not valid json"
    good = json.dumps(
        {
            "products": [{"name": "milk"}],
            "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0},
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.8,
        }
    )
    agent, client = _agent_with_responses([bad, good], prompt_manager)

    result = agent.extract("I need milk")

    assert result.products[0].name == "milk"
    assert len(client.calls) == 2


def test_extract_recovers_max_delivery_minutes_from_canonical_biryani_request(
    prompt_manager: PromptManager,
) -> None:
    """Regression test from the first Phase 4 bugfix (nullable-schema
    incident) -- kept here to guard both incidents simultaneously.
    """

    canonical_request = (
        "I am making biryani. I need onions and curd. Find the cheapest "
        "option that can deliver within 20 minutes."
    )
    llm_output = json.dumps(
        {
            "products": [{"name": "onion"}, {"name": "curd"}],
            "constraints": {
                "max_delivery_minutes": 20,
                "priority": "cheapest",
                "max_budget": 0,
            },
            "needs_clarification": False,
            "clarification_reason": "",
            "confidence": 0.9,
        }
    )
    agent, _ = _agent_with_responses([llm_output], prompt_manager)

    result = agent.extract(canonical_request)

    assert result.constraints.max_delivery_minutes == 20
    assert result.constraints.priority.value == "cheapest"
    assert result.constraints.max_budget is None


def test_extracted_constraints_schema_has_no_nullable_delivery_minutes_field() -> None:
    schema = _ExtractedConstraints.model_json_schema()

    assert "max_delivery_minutes" in schema.get("required", [])
    field_schema = schema["properties"]["max_delivery_minutes"]
    assert "anyOf" not in field_schema
    assert field_schema.get("type") == "integer"
