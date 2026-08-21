"""Ranking Engine.

Per Phase 0 architecture doc, section 5.2/11, and the master phase
plan's explicit instruction: deterministic ranking supporting cheapest,
fastest, best_value, and user constraints. **Never uses an LLM** — this
is enforced structurally (zero import of anything under ``app.core.llm``
or ``app.agents``, checked explicitly by
``test_ranking_never_imports_the_llm_layer``), not just by convention.

## Design: ranking is per-product, not per-basket

Phase 0's ``RankedResult`` contract wraps exactly one ``NormalizedProduct``,
not a multi-item basket — so this engine ranks each REQUESTED PRODUCT
independently across its cross-store options (e.g. "which store has the
cheapest onion"), rather than trying to pick one overall best store for
the whole order. Combining per-product rankings into a single
store-level recommendation ("order everything from Zepto") is
Recommendation Generation's job (Phase 12), not this layer's — guessing
at that aggregation logic now would mean designing Phase 12 early.

## Priority resolution: where Constraints.priority's nullability finally
   gets consumed

``Constraints.priority`` is ``Optional`` — made nullable specifically in
the Phase 4→5 deferred fix so the Ranking Engine, not the domain model or
the extraction layer, would own the "no preference stated" default.
``None`` is resolved to ``Priority.BEST_VALUE`` right here, in
``resolve_priority()`` — nowhere upstream, and nowhere else downstream.

## Hard constraints vs. scoring

``max_delivery_minutes``/``max_budget`` are user-stated LIMITS, not soft
preferences — a product exceeding either is filtered out entirely
(``apply_hard_constraints``), not merely scored lower. Out-of-stock
products are filtered the same way.

## The best_value formula

Equal-weighted min-max normalization of price and ETA within the
candidate set: each dimension is scaled to [0, 1] (0 = best in this set,
1 = worst), then averaged. A 70/30 price-weighted alternative was
considered and rejected for now — there's no real user data yet to
justify skewing either direction; equal weighting is the defensible
neutral default, explicitly flagged as tunable.
"""

from pydantic import BaseModel

from app.domain.constraints import Constraints, Priority
from app.domain.normalized_product import NormalizedProduct
from app.domain.ranked_result import RankedResult
from app.processing._scoring_utils import min_max_normalize as _min_max_normalize


def resolve_priority(priority: Priority | None) -> Priority:
    """``None`` means the user stated no preference — defaults to
    ``BEST_VALUE`` here, per the Phase 4→5 design decision. This is the
    ONLY place in the codebase that applies this default.
    """

    return priority if priority is not None else Priority.BEST_VALUE


def apply_hard_constraints(
    products: list[NormalizedProduct], constraints: Constraints
) -> tuple[list[NormalizedProduct], int]:
    """Filter by ``max_delivery_minutes``/``max_budget`` (hard ceilings
    the user explicitly stated) and by stock availability.

    Returns ``(surviving products, how many were excluded)``.
    """

    original_count = len(products)
    filtered = [product for product in products if product.in_stock]

    if constraints.max_delivery_minutes is not None:
        filtered = [
            p for p in filtered if p.eta_minutes <= constraints.max_delivery_minutes
        ]
    if constraints.max_budget is not None:
        filtered = [p for p in filtered if p.price_inr <= constraints.max_budget]

    return filtered, original_count - len(filtered)


def _score_products(
    products: list[NormalizedProduct], priority: Priority
) -> list[float]:
    """Compute a score per product — LOWER is always better, uniformly
    across all three priority modes, so sorting logic never needs to
    know which mode produced the score.
    """

    if priority == Priority.CHEAPEST:
        return [p.price_inr for p in products]

    if priority == Priority.FASTEST:
        return [float(p.eta_minutes) for p in products]

    # BEST_VALUE — see module docstring for the formula's rationale.
    price_norm = _min_max_normalize([p.price_inr for p in products])
    eta_norm = _min_max_normalize([float(p.eta_minutes) for p in products])
    return [(pn + en) / 2 for pn, en in zip(price_norm, eta_norm)]


def _rationale_for(
    product: NormalizedProduct, priority: Priority, rank: int
) -> str | None:
    """Short, deterministic, templated explanation for the TOP-ranked
    result only — NOT LLM-generated (master rule: Ranking must never use
    an LLM). Phase 12's Recommendation Generator produces the real
    natural-language explanation; this is just a factual, debuggable note.
    """

    if rank != 1:
        return None

    if priority == Priority.CHEAPEST:
        return f"Cheapest option: ₹{product.price_inr:.2f}"
    if priority == Priority.FASTEST:
        return f"Fastest option: {product.eta_minutes} min"
    return f"Best value: ₹{product.price_inr:.2f}, {product.eta_minutes} min"


def rank_products_for_one_item(
    products: list[NormalizedProduct], constraints: Constraints
) -> tuple[list[RankedResult], int]:
    """Rank one requested product's cross-store options.

    Returns ``(ranked results, excluded_count)`` — ``ranked`` is empty
    (not an error) if every candidate was filtered out by hard
    constraints; the caller decides what that means for the user.
    """

    priority = resolve_priority(constraints.priority)
    filtered, excluded_count = apply_hard_constraints(products, constraints)

    if not filtered:
        return [], excluded_count

    scores = _score_products(filtered, priority)
    order = sorted(range(len(filtered)), key=lambda i: scores[i])

    ranked: list[RankedResult] = []
    for position, index in enumerate(order, start=1):
        ranked.append(
            RankedResult(
                product=filtered[index],
                rank=position,
                score=scores[index],
                rationale=_rationale_for(filtered[index], priority, position),
            )
        )
    return ranked, excluded_count


import re

_STOP_WORDS = frozenset(
    {"a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "and", "or", "bar", "pack", "pkt"}
)


def _is_relevant_match(candidate_title: str, requested_name: str) -> bool:
    """Determine whether candidate_title is relevant to requested_name."""
    c_clean = candidate_title.strip().lower()
    r_clean = requested_name.strip().lower()

    if r_clean in c_clean or c_clean in r_clean:
        return True

    r_words = [w for w in re.findall(r"[a-z0-9]+", r_clean) if len(w) > 2 and w not in _STOP_WORDS]
    if not r_words:
        r_words = [w for w in re.findall(r"[a-z0-9]+", r_clean) if w not in _STOP_WORDS]

    if not r_words:
        return True

    c_words = set(re.findall(r"[a-z0-9]+", c_clean))
    matching_words = [w for w in r_words if w in c_words]

    if len(r_words) == 1:
        return len(matching_words) >= 1
    return len(matching_words) >= max(1, len(r_words) // 2)


class RankingSummary(BaseModel):
    """The Ranking Engine's complete output — one ranked list per
    requested product name, plus the resolved priority and per-product
    exclusion counts for transparency.
    """

    rankings: dict[str, list[RankedResult]]
    priority_used: Priority
    excluded_counts: dict[str, int]


def rank_search_results(
    normalized_products: list[NormalizedProduct],
    constraints: Constraints,
    requested_products: list[str] | None = None,
) -> RankingSummary:
    """The Ranking Engine's single entry point.

    If ``requested_products`` is provided (e.g. from the user's intent),
    matches candidates to each requested product and filters out irrelevant
    search results. If omitted, groups directly by ``product_name``.
    """

    priority = resolve_priority(constraints.priority)

    by_product: dict[str, list[NormalizedProduct]] = {}
    if requested_products is not None:
        for req_name in requested_products:
            req_clean = req_name.strip().lower()
            matching_candidates = [
                p for p in normalized_products
                if _is_relevant_match(p.product_name, req_clean)
            ]
            by_product[req_clean] = matching_candidates
    else:
        for product in normalized_products:
            by_product.setdefault(product.product_name, []).append(product)

    rankings: dict[str, list[RankedResult]] = {}
    excluded_counts: dict[str, int] = {}

    for name, group in by_product.items():
        ranked, excluded = rank_products_for_one_item(group, constraints)
        rankings[name] = ranked
        excluded_counts[name] = excluded

    return RankingSummary(
        rankings=rankings, priority_used=priority, excluded_counts=excluded_counts
    )
