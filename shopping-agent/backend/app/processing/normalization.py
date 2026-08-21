"""Normalization Layer.

Per Phase 0 architecture doc, section 5.2 and the master phase plan's
explicit instruction for this phase: normalize products from every store
into a common schema, and explain every normalization rule. This module
maps already-verified (Phase 9) but still string-typed
``RawProductResult`` entries into fully-typed ``NormalizedProduct``
entries — the contract every downstream phase (Ranking, Recommendation,
Order Execution) consumes.

Deterministic Python only — no LLM, no Appium dependency. Standalone,
not wired into the Phase 5 LangGraph workflow — same reasoning
established in Phases 7, 8, and 9 (Phase 15 is the integration point).

## Every normalization rule, explicitly

1. **Title**: trimmed and lowercased — the exact same convention already
   used for ``ProductRequest.name`` (Phase 4), so a normalized result's
   name and the user's originally-requested product name are always
   directly comparable without re-normalizing on either side.

2. **Price**: reuses Phase 9's ``parse_price()`` (currency-symbol
   stripping, comma removal, must parse to a positive float) rather than
   reimplementing it — DRY, and guarantees identical price-parsing
   behavior across Verification and Normalization.

3. **ETA**: extracts hour and minute components separately via regex
   (``parse_eta_minutes``), then combines them (``hours * 60 +
   minutes``). Handles compound values correctly — "1 hr 30 mins" → 90,
   not a naive 30×60. When a RANGE is present (e.g. "15-20 mins"), the
   UPPER bound is taken — see module-level design note above for why.
   Genuinely unparseable text (e.g. "just now", with no recognizable
   number+unit) returns ``None``.

4. **Quantity**: extracts the first ``<number><unit>`` pattern found
   (e.g. "1 kg" → ``(1.0, "kg")``, "500g" → ``(500.0, "g")``).
   Deliberately does NOT canonicalize units (e.g. converting "g" to
   "kg", or "ml" to "litre") — see known limitations in Phase 10 docs
   for why that's explicitly out of scope for this phase.

5. **in_stock**: always ``True`` for every successfully normalized
   product — ``RawProductResult`` has no stock-status field to derive
   this from (Phase 0's own spec doesn't include one). An honest
   placeholder, not an inferred value.

6. **All-or-nothing per item**: if ANY of price/ETA/quantity fails to
   parse, the ENTIRE item is dropped (not partially normalized with a
   fabricated value for the unparseable field) and reported as a
   ``NormalizationIssue`` — never silently discarded, matching the
   Phase 9 precedent of an always-visible audit trail.
"""

import re

from pydantic import BaseModel

from app.domain.normalized_product import NormalizedProduct
from app.domain.raw_product_result import RawProductResult
from app.processing.verification import parse_price

_HOUR_PATTERN = re.compile(r"(\d+)\s*(?:hr|hour)")
_MINUTE_PATTERN = re.compile(r"(\d+)\s*(?:min)")
_BARE_NUMBER_PATTERN = re.compile(r"\d+")
_QUANTITY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)")


class NormalizationIssue(BaseModel):
    """One item that couldn't be fully normalized, and why."""

    store_id: str
    product_name: str
    detail: str


class NormalizationResult(BaseModel):
    """The Normalization Layer's complete output."""

    normalized_products: list[NormalizedProduct]
    issues: list[NormalizationIssue]


def parse_eta_minutes(raw_eta: str) -> int | None:
    """Parse a delivery-time string into a whole number of minutes.

    See rule 3 in the module docstring for the full explanation
    (compound hr+min handling, range-takes-upper-bound). Returns
    ``None`` for anything with no recognizable number, never raises.
    """

    text = raw_eta.strip().lower()

    hour_matches = [int(m) for m in _HOUR_PATTERN.findall(text)]
    minute_matches = [int(m) for m in _MINUTE_PATTERN.findall(text)]

    if hour_matches or minute_matches:
        hours = max(hour_matches) if hour_matches else 0
        minutes = max(minute_matches) if minute_matches else 0
        total = hours * 60 + minutes
        return total if total > 0 else None

    # No explicit hr/min unit found — fall back to any bare number
    # (e.g. a store showing "15-20" with no unit word at all).
    bare_numbers = [int(m) for m in _BARE_NUMBER_PATTERN.findall(text)]
    if not bare_numbers:
        return None
    value = max(bare_numbers)
    return value if value > 0 else None


def parse_quantity(raw_quantity: str) -> tuple[float, str] | None:
    """Parse a quantity string into ``(value, unit)``.

    See rule 4 in the module docstring — units are extracted as-is, not
    canonicalized. Returns ``None`` if no ``<number><unit>`` pattern is
    found, or the number is not positive.
    """

    text = raw_quantity.strip().lower()
    match = _QUANTITY_PATTERN.search(text)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)
    if value <= 0:
        return None
    return value, unit


def _normalize_title(raw_title: str) -> str:
    """Rule 1: trim + lowercase, matching ``ProductRequest.name``'s
    normalization convention exactly (Phase 4).
    """

    return raw_title.strip().lower()


def normalize_verified_results(
    valid_results: list[RawProductResult],
) -> NormalizationResult:
    """Map already-verified raw results into the common ``NormalizedProduct``
    schema.

    Expects its input to already be Phase 9-verified (valid prices,
    deduplicated) — but does NOT assume this blindly: price is
    re-validated defensively via the same ``parse_price()`` Phase 9
    uses, since this function must remain correct and independently
    testable even if called with data that skipped Verification.
    """

    normalized: list[NormalizedProduct] = []
    issues: list[NormalizationIssue] = []

    for result in valid_results:
        price = parse_price(result.raw_price)
        eta = parse_eta_minutes(result.raw_eta)
        quantity_and_unit = parse_quantity(result.raw_quantity)

        problems: list[str] = []
        if price is None:
            problems.append(f"unparseable price '{result.raw_price}'")
        if eta is None:
            problems.append(f"unparseable ETA '{result.raw_eta}'")
        if quantity_and_unit is None:
            problems.append(f"unparseable quantity '{result.raw_quantity}'")

        if problems:
            issues.append(
                NormalizationIssue(
                    store_id=result.store_id,
                    product_name=result.raw_title,
                    detail="; ".join(problems),
                )
            )
            continue

        quantity, unit = quantity_and_unit
        normalized.append(
            NormalizedProduct(
                store_id=result.store_id,
                product_name=_normalize_title(result.raw_title),
                price_inr=price,  # type: ignore[arg-type]  # guaranteed non-None above
                eta_minutes=eta,  # type: ignore[arg-type]
                quantity=quantity,
                unit=unit,
                in_stock=True,  # rule 5 — see module docstring
            )
        )

    return NormalizationResult(normalized_products=normalized, issues=issues)
