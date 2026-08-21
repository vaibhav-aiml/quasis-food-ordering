"""Basket-level store selection.

Deterministic Python — no LLM. This is the aggregation step Phase 11's
own docs explicitly flagged as deferred: Ranking (Phase 11) ranks
per-product ("which store has the cheapest onion"), because Phase 0's
``RankedResult`` contract locks that in. A recommendation needs to name
ONE store for the whole order — this module is where that single
decision gets made, before the Recommendation Generator (the LLM-backed
agent) is ever asked to explain anything.
"""

from pydantic import BaseModel

from app.shared.domain.constraints import Priority
from app.grocery.domain.ranked_result import RankedResult
from app.grocery.processing._scoring_utils import min_max_normalize
from app.grocery.processing.ranking import RankingSummary


class StoreBasketSummary(BaseModel):
    """One store's ability to fulfill the entire requested basket, built
    from Phase 11's per-product rankings.
    """

    store_id: str
    matched_products: list[RankedResult]
    missing_products: list[str]
    total_price_inr: float
    max_eta_minutes: int
    fulfills_all_products: bool


def select_best_store(
    ranking_summary: RankingSummary,
    selected_indices: dict[str, int] | None = None,
) -> StoreBasketSummary | None:
    """Deterministically pick ONE store to recommend for the whole order.

    Selection policy:
    1. Prefer stores that have EVERY requested product (fewest missing
       products first — a store missing 0 items always beats a store
       missing 1, regardless of price/speed).
    2. Among equally-complete stores, rank by the resolved priority:
       ``CHEAPEST`` → lowest total basket price; ``FASTEST`` → lowest
       worst-case ETA across the basket; ``BEST_VALUE`` → equal-weighted
       normalized combination of both, using the exact same
       ``min_max_normalize`` Phase 11 uses for per-product scoring.

    If ``selected_indices`` is supplied, picks the specified candidate index
    for that product instead of default top rank (index 0).

    Returns ``None`` if every product's ranking was empty (nothing
    survived Phase 11's hard-constraint filtering for anything) — the
    caller (Recommendation Generator) is expected to skip the LLM
    entirely in that case, not ask it to explain an empty result.
    """

    product_names = list(ranking_summary.rankings.keys())
    if not product_names:
        return None

    all_store_ids: set[str] = set()
    for ranked_list in ranking_summary.rankings.values():
        all_store_ids.update(result.product.store_id for result in ranked_list)

    if not all_store_ids:
        return None

    baskets: list[StoreBasketSummary] = []
    for store_id in all_store_ids:
        matched: list[RankedResult] = []
        missing: list[str] = []

        for name in product_names:
            store_candidates = [
                result
                for result in ranking_summary.rankings[name]
                if result.product.store_id == store_id
            ]
            if not store_candidates:
                missing.append(name)
                continue

            target_idx = 0
            if selected_indices and name in selected_indices:
                idx = selected_indices[name]
                if 0 <= idx < len(store_candidates):
                    target_idx = idx

            matched.append(store_candidates[target_idx])

        if not matched:
            continue  # this store contributed nothing to any product

        baskets.append(
            StoreBasketSummary(
                store_id=store_id,
                matched_products=matched,
                missing_products=missing,
                total_price_inr=sum(r.product.price_inr for r in matched),
                max_eta_minutes=max(r.product.eta_minutes for r in matched),
                fulfills_all_products=(len(missing) == 0),
            )
        )

    if not baskets:
        return None

    priority = ranking_summary.priority_used
    scores = _basket_scores(baskets, priority)

    ranked_indices = sorted(
        range(len(baskets)),
        key=lambda i: (len(baskets[i].missing_products), scores[i]),
    )
    return baskets[ranked_indices[0]]


def _basket_scores(baskets: list[StoreBasketSummary], priority: Priority) -> list[float]:
    """Lower is better, matching Phase 11's ``_score_products`` convention."""

    if priority == Priority.CHEAPEST:
        return [b.total_price_inr for b in baskets]

    if priority == Priority.FASTEST:
        return [float(b.max_eta_minutes) for b in baskets]

    price_norm = min_max_normalize([b.total_price_inr for b in baskets])
    eta_norm = min_max_normalize([float(b.max_eta_minutes) for b in baskets])
    return [(p + e) / 2 for p, e in zip(price_norm, eta_norm)]
