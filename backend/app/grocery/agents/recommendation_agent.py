"""Recommendation Generator.

The first LLM-backed component since Phase 4's Intent Understanding
Agent, and it applies every lesson from that phase's two hardening
rounds: schema-constrained decoding with a required (never
Optional/nullable) output field, and — critically — deterministic
Python fact-checking of the LLM's output before trusting it, with a safe
template fallback when that check fails.

## What the LLM does and does not decide

Which store to recommend is ALREADY DECIDED before this class is ever
called — by ``app.grocery.processing.recommendation_selection.select_best_store``,
pure deterministic Python (rule #1/#2). The LLM's only job is to phrase
already-known, already-verified facts into a friendly sentence. It never
picks a store, never invents a price, and never sees anything it isn't
explicitly handed in the prompt.

## Fact-checking the LLM's output

After generation, the explanation text is checked for two things: does
it mention the recommended store's name, and does it mention the exact
formatted total price? This is the same substring-verification
philosophy as Phase 4's ``_filter_unsupported_products`` — applied here
to a generation task instead of an extraction task. If either check
fails, the LLM's output is discarded entirely in favor of a deterministic,
Python-only template — an explanation that's blander but never
unverifiable beats a fluent one that might have quietly dropped or
distorted the facts it was given.
"""

import logging

from pydantic import BaseModel, Field

from app.core.llm.exceptions import LLMConnectionError, LLMValidationError
from app.core.llm.structured import StructuredLLMService
from app.shared.domain.constraints import Priority
from app.grocery.processing.recommendation_selection import StoreBasketSummary

_logger = logging.getLogger("app.grocery.agents.recommendation")

_PRIORITY_LABELS: dict[Priority, str] = {
    Priority.CHEAPEST: "cheapest",
    Priority.FASTEST: "fastest",
    Priority.BEST_VALUE: "best overall value",
}


class _ExplanationOutput(BaseModel):
    """The LLM's output contract — a single required field, so there's
    no Optional/nullable field for a schema-constrained decoder to get
    wrong (see Phase 4's Incident 1 for why that lesson matters here too).
    """

    explanation: str = Field(
        min_length=1,
        description="A friendly 2-3 sentence explanation using ONLY the given facts.",
    )


class RecommendationResult(BaseModel):
    """Final output of this agent."""

    store_id: str | None
    explanation: str
    used_fallback: bool
    basket: StoreBasketSummary | None


def _fallback_explanation(basket: StoreBasketSummary, priority: Priority) -> str:
    """Deterministic, Python-only explanation. Used whenever the LLM's
    output can't be trusted (connection/validation failure, or failed
    the post-generation fact-check) — or could be used standalone
    without any LLM at all.
    """

    if priority == Priority.CHEAPEST:
        basis = f"the lowest total price (Rs. {basket.total_price_inr:.2f})"
    elif priority == Priority.FASTEST:
        basis = f"the fastest delivery ({basket.max_eta_minutes} min)"
    else:
        basis = (
            f"the best overall balance of price (Rs. {basket.total_price_inr:.2f}) "
            f"and delivery time ({basket.max_eta_minutes} min)"
        )

    text = f"{basket.store_id.capitalize()} was selected based on {basis}."
    if not basket.fulfills_all_products:
        missing = ", ".join(basket.missing_products)
        text += f" Note: {missing} could not be found at this store."
    return text


def _explanation_mentions_key_facts(explanation: str, basket: StoreBasketSummary) -> bool:
    """The fact-check: does the LLM's output actually mention the store
    it was told to talk about, and the exact price it was given?
    """

    text = explanation.lower()
    store_mentioned = basket.store_id.lower() in text
    price_mentioned = f"{basket.total_price_inr:.2f}" in explanation
    return store_mentioned and price_mentioned


def _build_facts_variables(
    basket: StoreBasketSummary, priority: Priority
) -> dict[str, str]:
    matched_names = ", ".join(r.product.product_name for r in basket.matched_products)
    if basket.missing_products:
        missing_line = (
            "- Products NOT available at this store: "
            + ", ".join(basket.missing_products)
        )
    else:
        missing_line = "- All requested products are available at this store."

    return {
        "store_id": basket.store_id,
        "priority": _PRIORITY_LABELS[priority],
        "total_price": f"{basket.total_price_inr:.2f}",
        "max_eta": str(basket.max_eta_minutes),
        "matched_products_list": matched_names,
        "missing_products_section": missing_line,
    }


class RecommendationGenerator:
    """Generates a natural-language explanation for an already-selected
    store recommendation.
    """

    def __init__(self, llm: StructuredLLMService) -> None:
        self._llm = llm

    def generate(
        self, basket: StoreBasketSummary | None, priority: Priority
    ) -> RecommendationResult:
        """Generate the final recommendation explanation.

        If ``basket`` is ``None`` (nothing survived Ranking's hard
        constraints for any product), the LLM is never called — same
        "don't ask the LLM about nothing" principle as Phase 4's
        pre-LLM short-circuit.
        """

        if basket is None:
            return RecommendationResult(
                store_id=None,
                explanation=(
                    "No matching products were found at any store for "
                    "this request."
                ),
                used_fallback=True,
                basket=None,
            )

        variables = _build_facts_variables(basket, priority)

        try:
            extracted = self._llm.generate(
                template_name="recommendation_explanation",
                response_model=_ExplanationOutput,
                variables=variables,
            )
        except (LLMConnectionError, LLMValidationError):
            _logger.warning(
                "recommendation_llm_call_failed",
                extra={"store_id": basket.store_id},
            )
            return RecommendationResult(
                store_id=basket.store_id,
                explanation=_fallback_explanation(basket, priority),
                used_fallback=True,
                basket=basket,
            )

        if _explanation_mentions_key_facts(extracted.explanation, basket):
            return RecommendationResult(
                store_id=basket.store_id,
                explanation=extracted.explanation,
                used_fallback=False,
                basket=basket,
            )

        _logger.warning(
            "recommendation_llm_output_failed_fact_check",
            extra={"store_id": basket.store_id, "raw_explanation": extracted.explanation},
        )
        return RecommendationResult(
            store_id=basket.store_id,
            explanation=_fallback_explanation(basket, priority),
            used_fallback=True,
            basket=basket,
        )
