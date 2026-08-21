"""Intent Understanding Agent.

Turns a user's free-text shopping request into a validated
``IntentRequest``. This is the first node in the LangGraph workflow
(Phase 5) and the only place in the system that asks an LLM "what does the
user want?" — everything downstream (planning, ranking, ordering) operates
on the structured ``IntentRequest`` this agent produces, never on raw text
again.

## Extraction-only policy (Phase 4 bugfix log)

A live test found the LLM inventing products and constraints for vague
input ("get me something for dinner" -> chicken, rice, vegetables,
60-minute delivery, ₹500 budget — none of which the user said). Prompt
wording alone can't be trusted to prevent this reliably, so this module
enforces an extraction-only policy in three independent layers:

0. **Pre-LLM** (`_looks_obviously_vague`, this file): requests made up
   entirely of generic filler words ("get me something for dinner", "I
   need food", "buy something") never reach the LLM at all. The model has
   no memory of this user's preferences, past orders, or dietary needs —
   asking it to fill in "something for dinner" is asking it to invent an
   answer by definition, no matter how the prompt is worded. Recognizing
   that a request carries no extractable information is the system's job,
   not the model's guess.
1. **Prompt-level** (`intent_extraction.txt`): explicit "never invent"
   instructions plus few-shot examples covering exactly this failure mode,
   for requests that DO reach the LLM but are still ambiguous.
2. **Deterministic Python-level, post-LLM**: regardless of what the LLM
   claims, every product and every numeric constraint is checked against
   the user's actual raw text before being trusted. A product whose name
   doesn't literally appear in the input is dropped. A numeric constraint
   is zeroed out if the input contains no digits at all. An empty product
   list — whether because the user said nothing concrete or because
   everything the LLM claimed got rejected — always forces
   ``needs_clarification=True`` with confidence capped low.

Layers 0 and 2 are what actually matter for correctness: they hold even if
the LLM completely ignores its instructions, or is never consulted at all.
"""

import logging
import re
from enum import Enum

from pydantic import BaseModel, Field

from app.core.llm.structured import StructuredLLMService
from app.domain.constraints import Constraints, Priority
from app.domain.intent import CLARIFICATION_CONFIDENCE_CEILING, IntentRequest
from app.domain.product import ProductRequest

_logger = logging.getLogger("app.agents.intent")

DEFAULT_CLARIFICATION_REASON = (
    "The request did not clearly specify which products to buy."
)

# Generic filler words that carry no product information on their own. A
# request built ENTIRELY out of these words (e.g. "get me something for
# dinner") is treated as carrying zero extractable information and never
# reaches the LLM — see _looks_obviously_vague.
_VAGUE_ONLY_WORDS = frozenset(
    {
        "a", "an", "and", "anything", "buy", "dinner", "food", "for",
        "get", "groceries", "i", "lunch", "me", "my", "need", "of",
        "or", "order", "please", "snack", "snacks", "some", "something",
        "stuff", "the", "to", "us", "want", "we", "whatever",
    }
)


def _looks_obviously_vague(raw_text: str) -> bool:
    """Deterministic pre-LLM check for requests with no concrete product
    nouns at all — e.g. "get me something for dinner", "I need food",
    "buy something".

    This exists so requests like these never reach the LLM in the first
    place: the model has no memory of this user's preferences or past
    orders, so asking it to guess "something for dinner" is asking it to
    invent an answer by construction, regardless of prompt wording. The
    system — deterministic Python, not the model — is what recognizes a
    low-information request and defers to the user for more context.

    Deliberately conservative: only returns True when EVERY word in the
    (punctuation-stripped, lowercased) request is in a small, fixed set of
    generic/filler words. Any word outside that set (e.g. "onion",
    "biryani", "milk") means there's at least one candidate product noun,
    so the request is sent to the LLM to extract properly. A false
    negative here (treating a genuinely vague request as extractable) is
    still caught afterward by the post-LLM sanitization layers — this is
    a fast-path optimization and a stronger guarantee for the clearest
    cases, not the only safety net.
    """

    words = re.findall(r"[a-zA-Z']+", raw_text.lower())
    if not words:
        return True
    return all(word in _VAGUE_ONLY_WORDS for word in words)


class _ExtractedPriority(str, Enum):
    """LLM-facing priority enum — one extra value beyond the domain
    ``Priority`` enum: ``UNSPECIFIED``.

    Kept deliberately separate from ``app.domain.constraints.Priority``
    rather than adding a 4th value there: ``UNSPECIFIED`` is an
    extraction-only concept ("the user said nothing about this") that has
    no business leaking into the domain model, which should only ever
    represent real, stated user preferences.

    Still required and non-nullable on ``_ExtractedConstraints`` — this
    is what keeps the Incident-1 lesson intact: representing optionality
    via an explicit sentinel *value* within a required, singly-typed
    field, never via a nullable/omittable field.
    """

    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST_VALUE = "best_value"
    UNSPECIFIED = "unspecified"


_PRIORITY_MAP: dict[_ExtractedPriority, Priority | None] = {
    _ExtractedPriority.CHEAPEST: Priority.CHEAPEST,
    _ExtractedPriority.FASTEST: Priority.FASTEST,
    _ExtractedPriority.BEST_VALUE: Priority.BEST_VALUE,
    _ExtractedPriority.UNSPECIFIED: None,
}


class _ExtractedConstraints(BaseModel):
    """LLM-facing constraints schema.

    Uses required, non-nullable fields with sentinel "not stated" values
    (``0`` for both numeric fields, ``unspecified`` for priority) instead
    of ``Optional``/nullable types — see the Phase 4 bugfix log
    (incident 1) for why: a field that is both nullable and excluded from
    JSON Schema's ``required`` list is a documented failure mode for
    schema-constrained LLM decoding.
    """

    max_delivery_minutes: int = Field(
        ge=0,
        description=(
            "Maximum delivery time in minutes EXPLICITLY stated by the "
            "user, or 0 if none was stated. Never guess a typical value."
        ),
    )
    priority: _ExtractedPriority = Field(
        description=(
            "Ranking priority inferred ONLY from explicit wording, or "
            "'unspecified' if the user expressed no preference at all."
        )
    )
    max_budget: float = Field(
        ge=0,
        description=(
            "Maximum total budget in INR EXPLICITLY stated by the user, "
            "or 0 if none was stated. Never guess a typical value."
        ),
    )


class _ExtractedIntent(BaseModel):
    """The shape the LLM actually produces.

    Deliberately excludes ``raw_text`` — see module docstring. Intentionally
    private: nothing outside this module should construct or depend on it.

    ``needs_clarification`` / ``clarification_reason`` are required (no
    Python default) for the same reason every other field here is required:
    a field the model can silently omit is a field the model will silently
    get wrong under pressure. ``clarification_reason`` uses ``""`` as its
    "not needed" sentinel, consistent with the numeric sentinel pattern.
    """

    products: list[ProductRequest] = Field(
        description=(
            "Products EXPLICITLY named by the user. Empty list if the "
            "user did not name any specific product — never guess."
        )
    )
    constraints: _ExtractedConstraints
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = Field(
        description=(
            "True if the request does not name specific, actionable "
            "products, or is otherwise too ambiguous to extract safely."
        )
    )
    clarification_reason: str = Field(
        description=(
            "Brief reason clarification is needed, or empty string "
            "if needs_clarification is false."
        )
    )


def merge_duplicate_products(products: list[ProductRequest]) -> list[ProductRequest]:
    """Combine products the LLM extracted as separate entries but that
    refer to the same thing.

    Two products are considered duplicates if they have the same
    (already-normalized) ``name`` and the same ``unit`` — in that case
    their quantities are summed. Same name with *different* units is
    deliberately NOT merged, since summing across incompatible units
    would silently produce a wrong number; both entries are kept as-is.
    """

    merged: dict[tuple[str, str], ProductRequest] = {}
    order: list[tuple[str, str]] = []

    for product in products:
        key = (product.name, product.unit)
        if key in merged:
            existing = merged[key]
            merged[key] = ProductRequest(
                name=existing.name,
                quantity=existing.quantity + product.quantity,
                unit=existing.unit,
            )
        else:
            merged[key] = product
            order.append(key)

    return [merged[key] for key in order]


def _filter_unsupported_products(
    products: list[ProductRequest], raw_text: str
) -> tuple[list[ProductRequest], list[str]]:
    """Drop any product whose name doesn't literally appear in the user's
    raw text, and report which ones were dropped.

    This is the deterministic backstop against the LLM inventing products
    a user never mentioned — it does not replace prompt instructions, it
    catches exactly the case where instruction-following fails despite the
    prompt saying not to invent.

    Deliberately simple (case-insensitive substring match) rather than
    fuzzy/NLP matching: a false negative here (rejecting a legitimately
    named product because of phrasing mismatch — e.g. the LLM translating
    "yogurt" to "curd") is far safer than a false positive (letting a
    hallucinated product through), given the cost of accidentally
    including something the user never asked for. Documented as a known
    limitation, not treated as a bug.
    """

    haystack = raw_text.lower()
    supported: list[ProductRequest] = []
    rejected: list[str] = []

    for product in products:
        if product.name in haystack:
            supported.append(product)
        else:
            rejected.append(product.name)

    return supported, rejected


def _sanitize_product_quantities(
    products: list[ProductRequest], raw_text: str
) -> list[ProductRequest]:
    """Reset quantity/unit to their neutral defaults for every product if
    the raw text contains no digits at all.

    A specific quantity like "2kg" should only ever come from the user's
    own words. If there isn't a single digit anywhere in the request, any
    non-default quantity/unit the LLM attached to a product is invented —
    exactly the reasoning behind ``_sanitize_constraints`` below, applied
    to products instead of constraints.
    """

    if any(char.isdigit() for char in raw_text):
        return products

    return [
        product
        if (product.quantity == 1.0 and product.unit == "unit")
        else ProductRequest(name=product.name, quantity=1.0, unit="unit")
        for product in products
    ]


def _sanitize_constraints(
    constraints: _ExtractedConstraints, raw_text: str
) -> _ExtractedConstraints:
    """Zero out any numeric constraint the LLM stated despite no digits
    appearing anywhere in the user's raw text.

    A concrete delivery-time or budget number should only ever come from
    the user's own words. If the raw text contains no digits at all, any
    nonzero number the LLM produced is, by definition, invented — this is
    exactly the mechanism that would have caught the reported
    ``max_delivery_minutes: 60, max_budget: 500.0`` hallucination for
    "get me something for dinner".

    Known limitation: a worded number with no digits (e.g. "half an
    hour") is conservatively zeroed too, since confirming it would need
    real NLP. Erring toward "unstated" rather than risking an invented
    number is the intentional tradeoff here — see Phase 4 known
    limitations.
    """

    if any(char.isdigit() for char in raw_text):
        return constraints

    if constraints.max_delivery_minutes == 0 and constraints.max_budget == 0:
        return constraints

    return _ExtractedConstraints(
        max_delivery_minutes=0,
        priority=constraints.priority,
        max_budget=0,
    )


def _to_domain_constraints(extracted: _ExtractedConstraints) -> Constraints:
    """Map the LLM's sentinel-based extraction to the domain's nullable
    ``Constraints``. Both the numeric ``0 -> None`` translation and the
    ``UNSPECIFIED -> None`` priority translation are deterministic Python,
    not part of the LLM's output contract.
    """

    return Constraints(
        max_delivery_minutes=extracted.max_delivery_minutes or None,
        priority=_PRIORITY_MAP[extracted.priority],
        max_budget=extracted.max_budget or None,
    )


def _enforce_extraction_policy(
    *,
    products: list[ProductRequest],
    llm_needs_clarification: bool,
    llm_clarification_reason: str,
    llm_confidence: float,
) -> tuple[bool, str | None, float]:
    """Deterministically decide the final clarification/confidence state —
    never trusts the LLM's self-report alone (rule: AI reasons, Python
    decides).

    Three independent triggers force ``needs_clarification=True``:

    1. No products survived extraction/sanitization — an empty product
       list can never be a "confidently ready to order" request.
    2. The LLM itself flagged the request as needing clarification (this
       includes the case where product-rejection notes were folded into
       ``llm_clarification_reason`` by the caller).
    3. The LLM's confidence fell below ``CLARIFICATION_CONFIDENCE_CEILING``,
       even if it claimed no clarification was needed — a low-confidence
       LLM claiming certainty is exactly the failure mode this exists to
       catch.

    Whenever clarification is required, confidence is deterministically
    capped at ``CLARIFICATION_CONFIDENCE_CEILING`` regardless of what the
    LLM reported, so "low-information requests have low confidence" holds
    even if the model's own number disagreed.
    """

    reasons: list[str] = []
    needs_clarification = False

    if not products:
        needs_clarification = True
        reasons.append("No specific products could be identified in the request.")

    if llm_needs_clarification:
        needs_clarification = True
        if llm_clarification_reason:
            reasons.append(llm_clarification_reason)

    if llm_confidence < CLARIFICATION_CONFIDENCE_CEILING:
        needs_clarification = True
        reasons.append(
            f"Extraction confidence ({llm_confidence:.2f}) was below the "
            f"acceptable threshold ({CLARIFICATION_CONFIDENCE_CEILING})."
        )

    if not needs_clarification:
        return False, None, llm_confidence

    reason = " ".join(dict.fromkeys(reasons)) or DEFAULT_CLARIFICATION_REASON
    confidence = min(llm_confidence, CLARIFICATION_CONFIDENCE_CEILING)
    return True, reason, confidence


class IntentUnderstandingAgent:
    """Extracts a structured ``IntentRequest`` from free-text user input."""

    def __init__(self, llm: StructuredLLMService) -> None:
        self._llm = llm

    def extract(self, raw_text: str) -> IntentRequest:
        """Extract intent from a user's shopping request.

        Args:
            raw_text: The user's original, unmodified input.

        Returns:
            A validated ``IntentRequest``. Requests carrying no concrete
            product information never reach the LLM at all (see
            ``_looks_obviously_vague``). For everything else, ``products``
            contains only items whose names are backed by the raw text;
            numeric constraints/quantities are zeroed if the raw text has
            no digits at all; ``needs_clarification`` is deterministically
            set whenever the above leaves nothing concrete, regardless of
            what the LLM itself claimed.

        Raises:
            ValueError: if ``raw_text`` is empty or whitespace-only.
            LLMConnectionError: if the LLM backend is unreachable.
            LLMValidationError: if the LLM never produced valid structured
                output within the configured retry budget.
        """

        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text must not be empty")

        if _looks_obviously_vague(raw_text):
            _logger.info(
                "intent_agent_short_circuited_vague_request",
                extra={"raw_text": raw_text},
            )
            return IntentRequest(
                raw_text=raw_text,
                products=[],
                constraints=Constraints(),
                confidence=0.0,
                needs_clarification=True,
                clarification_reason=(
                    "The request didn't name any specific products, so "
                    "nothing was guessed. Please say what you'd like to "
                    "buy, e.g. 'onions and curd for biryani'."
                ),
            )

        extracted = self._llm.generate(
            template_name="intent_extraction",
            response_model=_ExtractedIntent,
            variables={"user_message": raw_text},
        )

        merged = merge_duplicate_products(extracted.products)
        supported, rejected = _filter_unsupported_products(merged, raw_text)
        supported = _sanitize_product_quantities(supported, raw_text)
        sanitized_constraints = _sanitize_constraints(extracted.constraints, raw_text)

        llm_needs_clarification = extracted.needs_clarification
        llm_reason = extracted.clarification_reason

        if rejected:
            llm_needs_clarification = True
            rejection_note = (
                "Rejected product(s) not mentioned in the original request: "
                + ", ".join(rejected)
                + "."
            )
            llm_reason = (
                f"{llm_reason} {rejection_note}".strip()
                if llm_reason
                else rejection_note
            )
            _logger.warning(
                "intent_agent_rejected_unsupported_products",
                extra={"rejected_products": rejected, "raw_text": raw_text},
            )

        needs_clarification, reason, confidence = _enforce_extraction_policy(
            products=supported,
            llm_needs_clarification=llm_needs_clarification,
            llm_clarification_reason=llm_reason,
            llm_confidence=extracted.confidence,
        )

        return IntentRequest(
            raw_text=raw_text,
            products=supported,
            constraints=_to_domain_constraints(sanitized_constraints),
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_reason=reason,
        )
