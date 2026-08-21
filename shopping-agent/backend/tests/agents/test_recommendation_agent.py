"""Tests for app.agents.recommendation_agent.

Uses the same FakeLLMClient + real StructuredLLMService pattern proven in
Phase 3/4 — exercises real render/parse/validate/retry logic without a
real Ollama server. Every scenario here was also runtime-verified
directly in the sandbox that built this phase; see Phase 12 docs.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.recommendation_agent import (
    RecommendationGenerator,
    _build_facts_variables,
    _explanation_mentions_key_facts,
    _fallback_explanation,
)
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.domain.constraints import Priority
from app.domain.normalized_product import NormalizedProduct
from app.domain.ranked_result import RankedResult
from app.processing.recommendation_selection import StoreBasketSummary


def _product(store: str, name: str, price: float, eta: int) -> NormalizedProduct:
    return NormalizedProduct(
        store_id=store, product_name=name, price_inr=price, eta_minutes=eta,
        quantity=1.0, unit="kg",
    )


def _ranked(store: str, name: str, price: float, eta: int) -> RankedResult:
    return RankedResult(product=_product(store, name, price, eta), rank=1, score=price)


def _complete_basket() -> StoreBasketSummary:
    return StoreBasketSummary(
        store_id="zepto",
        matched_products=[_ranked("zepto", "onion", 10.0, 15), _ranked("zepto", "curd", 20.0, 15)],
        missing_products=[],
        total_price_inr=30.0,
        max_eta_minutes=15,
        fulfills_all_products=True,
    )


def _partial_basket() -> StoreBasketSummary:
    return StoreBasketSummary(
        store_id="blinkit",
        matched_products=[_ranked("blinkit", "onion", 12.0, 10)],
        missing_products=["curd"],
        total_price_inr=12.0,
        max_eta_minutes=10,
        fulfills_all_products=False,
    )


# --- _fallback_explanation -------------------------------------------------------------


def test_fallback_cheapest_mentions_store_and_price() -> None:
    text = _fallback_explanation(_complete_basket(), Priority.CHEAPEST)
    assert "Zepto" in text and "30.00" in text


def test_fallback_fastest_mentions_eta() -> None:
    text = _fallback_explanation(_complete_basket(), Priority.FASTEST)
    assert "15 min" in text


def test_fallback_best_value_mentions_both() -> None:
    text = _fallback_explanation(_complete_basket(), Priority.BEST_VALUE)
    assert "30.00" in text and "15 min" in text


def test_fallback_mentions_missing_products() -> None:
    text = _fallback_explanation(_partial_basket(), Priority.CHEAPEST)
    assert "curd" in text


# --- _explanation_mentions_key_facts -------------------------------------------------------------


def test_fact_check_passes_when_store_and_price_present() -> None:
    basket = _complete_basket()
    assert _explanation_mentions_key_facts("Zepto is great, total Rs. 30.00", basket) is True


def test_fact_check_fails_on_wrong_store() -> None:
    basket = _complete_basket()
    assert _explanation_mentions_key_facts("Blinkit is great, total Rs. 30.00", basket) is False


def test_fact_check_fails_on_wrong_price() -> None:
    basket = _complete_basket()
    assert _explanation_mentions_key_facts("Zepto is great, total Rs. 99.00", basket) is False


# --- _build_facts_variables -------------------------------------------------------------


def test_facts_variables_complete_basket() -> None:
    variables = _build_facts_variables(_complete_basket(), Priority.CHEAPEST)
    assert variables["store_id"] == "zepto"
    assert variables["total_price"] == "30.00"
    assert "All requested products are available" in variables["missing_products_section"]


def test_facts_variables_partial_basket() -> None:
    variables = _build_facts_variables(_partial_basket(), Priority.CHEAPEST)
    assert "curd" in variables["missing_products_section"]


# --- RecommendationGenerator.generate() (full integration) -------------------------------------------------------------


class FakeLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[Any] = []

    def chat(self, *, messages: list[dict], response_format: dict | None = None) -> str:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


@pytest.fixture
def prompt_manager(tmp_path: Path) -> PromptManager:
    (tmp_path / "recommendation_explanation.txt").write_text(
        "Schema: $schema\nStore: $store_id\nPriority: $priority\nPrice: $total_price\n"
        "Eta: $max_eta\nProducts: $matched_products_list\n$missing_products_section",
        encoding="utf-8",
    )
    return PromptManager(templates_dir=tmp_path)


def test_generate_skips_llm_entirely_when_basket_is_none(
    prompt_manager: PromptManager,
) -> None:
    client = FakeLLMClient([])
    generator = RecommendationGenerator(StructuredLLMService(client, prompt_manager))

    result = generator.generate(None, Priority.BEST_VALUE)

    assert result.store_id is None
    assert result.used_fallback is True
    assert len(client.calls) == 0


def test_generate_uses_llm_output_when_it_passes_fact_check(
    prompt_manager: PromptManager,
) -> None:
    good_output = json.dumps(
        {"explanation": "Zepto is recommended with a total of Rs. 30.00 for your order."}
    )
    client = FakeLLMClient([good_output])
    generator = RecommendationGenerator(StructuredLLMService(client, prompt_manager))

    result = generator.generate(_complete_basket(), Priority.CHEAPEST)

    assert result.used_fallback is False
    assert "Zepto" in result.explanation
    assert "30.00" in result.explanation


def test_generate_falls_back_when_llm_output_fails_fact_check(
    prompt_manager: PromptManager,
) -> None:
    bad_output = json.dumps({"explanation": "This store is great and costs Rs. 30.00 total."})
    client = FakeLLMClient([bad_output])
    generator = RecommendationGenerator(StructuredLLMService(client, prompt_manager))

    result = generator.generate(_complete_basket(), Priority.CHEAPEST)

    assert result.used_fallback is True
    assert "Zepto" in result.explanation  # the safe fallback DOES mention it correctly


def test_generate_falls_back_when_llm_never_produces_valid_json(
    prompt_manager: PromptManager,
) -> None:
    client = FakeLLMClient(["not json", "still not json", "nope"])
    generator = RecommendationGenerator(
        StructuredLLMService(client, prompt_manager, max_retries=2)
    )

    result = generator.generate(_complete_basket(), Priority.FASTEST)

    assert result.used_fallback is True
    assert "Zepto" in result.explanation
