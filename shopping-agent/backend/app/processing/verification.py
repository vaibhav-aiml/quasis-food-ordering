"""Verification Layer.

Per Phase 0 architecture doc, section 5.2 and section 12, and the master
phase plan's explicit scope for this phase: validate missing products,
duplicate products, failed automation, and invalid prices; surface a
retry-strategy signal. Deterministic Python only — no LLM, no Appium
dependency (rules #1/#2/#7). Everything here operates purely on
already-collected ``RawProductResult`` data, fully decoupled from HOW
that data was obtained (a real Appium adapter, a mock, or a test fixture
— this layer can't tell the difference and doesn't need to).

Deliberately NOT wired into the Phase 5 LangGraph workflow — see Phase 7
and Phase 8 docs for why (each phase's layer is built and tested
standalone; Phase 15 is the explicit integration point).
"""

from typing import Literal

from pydantic import BaseModel

from app.domain.product import ProductRequest
from app.domain.raw_product_result import RawProductResult

_CURRENCY_NOISE = ("₹", "Rs.", "Rs", "INR", "$", ",")


class VerificationIssue(BaseModel):
    """One thing this layer rejected or flagged, with enough context to
    log or debug — never silently dropped without a trace.
    """

    reason: Literal["invalid_price", "duplicate", "missing_product", "store_unavailable"]
    store_id: str | None
    product_name: str | None
    detail: str


class VerificationResult(BaseModel):
    """The Verification Layer's complete output: what survived, and a
    structured report of everything that didn't.
    """

    valid_results: list[RawProductResult]
    issues: list[VerificationIssue]
    missing_products: list[str]
    stores_needing_retry: list[str]


def parse_price(raw_price: str) -> float | None:
    """Attempt to parse a raw price string into a positive float.

    Returns ``None`` (never raises) for anything unparseable, zero, or
    negative — the caller decides what to do with an unparseable price;
    this function only answers "is this a usable number".
    """

    cleaned = raw_price.strip()
    for noise in _CURRENCY_NOISE:
        cleaned = cleaned.replace(noise, "")
    cleaned = cleaned.strip()

    try:
        value = float(cleaned)
    except ValueError:
        return None

    if value <= 0:
        return None
    return value


def verify_prices(
    results: list[RawProductResult],
) -> tuple[list[RawProductResult], list[VerificationIssue]]:
    """Split results into those with a parseable, positive price and
    those without — the latter reported as ``invalid_price`` issues.
    """

    valid: list[RawProductResult] = []
    issues: list[VerificationIssue] = []

    for result in results:
        if parse_price(result.raw_price) is None:
            issues.append(
                VerificationIssue(
                    reason="invalid_price",
                    store_id=result.store_id,
                    product_name=result.raw_title,
                    detail=(
                        f"Could not parse a valid positive price from "
                        f"'{result.raw_price}'."
                    ),
                )
            )
            continue
        valid.append(result)

    return valid, issues


def detect_duplicates(
    results: list[RawProductResult],
) -> tuple[list[RawProductResult], list[VerificationIssue]]:
    """Within the SAME store, the same (normalized) title appearing more
    than once is treated as a duplicate — the first occurrence is kept,
    later ones are flagged and dropped.

    Cross-store repeats of the same title are NOT duplicates — comparing
    the same product across stores is exactly what the rest of the
    pipeline (Ranking, Phase 11) needs.
    """

    seen: set[tuple[str, str]] = set()
    kept: list[RawProductResult] = []
    issues: list[VerificationIssue] = []

    for result in results:
        key = (result.store_id, result.raw_title.strip().lower())
        if key in seen:
            issues.append(
                VerificationIssue(
                    reason="duplicate",
                    store_id=result.store_id,
                    product_name=result.raw_title,
                    detail=(
                        f"Duplicate result for '{result.raw_title}' from "
                        f"store '{result.store_id}' — keeping first "
                        "occurrence."
                    ),
                )
            )
            continue
        seen.add(key)
        kept.append(result)

    return kept, issues


def detect_missing_products(
    requested: list[ProductRequest], valid_results: list[RawProductResult]
) -> list[str]:
    """Which requested products have zero valid results from any store.

    Uses case-insensitive substring containment — the same conservative,
    deterministic matching philosophy established in Phase 4's
    anti-hallucination fix (``_filter_unsupported_products``): a false
    "missing" is far safer than silently treating an unrelated result as
    a match for the wrong product.
    """

    found_titles = [result.raw_title.strip().lower() for result in valid_results]
    missing: list[str] = []

    for product in requested:
        if not any(product.name in title for title in found_titles):
            missing.append(product.name)

    return missing


def detect_stores_needing_retry(
    attempted_store_ids: list[str], valid_results: list[RawProductResult]
) -> list[str]:
    """Which attempted stores contributed ZERO valid results.

    This is a decision SIGNAL, not a retry executor — Phase 5's graph
    already implements the actual bounded retry loop
    (``retry_orchestration``); this function only answers "should that
    loop consider retrying this store", based on validated data, not raw
    (possibly automation-broken) data.
    """

    stores_with_valid_results = {result.store_id for result in valid_results}
    return [
        store_id
        for store_id in attempted_store_ids
        if store_id not in stores_with_valid_results
    ]


def verify_search_results(
    requested_products: list[ProductRequest],
    attempted_store_ids: list[str],
    raw_results: list[RawProductResult],
) -> VerificationResult:
    """The Verification Layer's single entry point.

    Pipeline order matters: price validation runs BEFORE duplicate
    detection, so that if two "duplicate" entries differ in price
    validity, the one with a genuinely valid price is what survives —
    not whichever happened to appear first in the raw list.
    """

    issues: list[VerificationIssue] = []

    valid, price_issues = verify_prices(raw_results)
    issues.extend(price_issues)

    valid, duplicate_issues = detect_duplicates(valid)
    issues.extend(duplicate_issues)

    missing_products = detect_missing_products(requested_products, valid)
    for product_name in missing_products:
        issues.append(
            VerificationIssue(
                reason="missing_product",
                store_id=None,
                product_name=product_name,
                detail=f"No valid results found for '{product_name}' from any store.",
            )
        )

    stores_needing_retry = detect_stores_needing_retry(attempted_store_ids, valid)
    for store_id in stores_needing_retry:
        issues.append(
            VerificationIssue(
                reason="store_unavailable",
                store_id=store_id,
                product_name=None,
                detail=f"Store '{store_id}' returned no valid results — may need retry.",
            )
        )

    return VerificationResult(
        valid_results=valid,
        issues=issues,
        missing_products=missing_products,
        stores_needing_retry=stores_needing_retry,
    )
