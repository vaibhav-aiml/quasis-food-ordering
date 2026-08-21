# Phase 11 — Ranking Engine

> **Status:** Deterministic ranking — cheapest, fastest, best_value, and
> user constraints. Zero LLM dependency, structurally verified. This is
> where `Constraints.priority`'s nullability finally gets consumed.

---

## 1. Goal

Rank `NormalizedProduct` options (per requested product, across stores)
by the user's stated priority, respecting hard constraints (delivery
time, budget) as filters rather than soft preferences. Master's explicit
instruction: **do not use an LLM** — enforced here structurally, not just
by convention.

---

## 2. Concepts to Learn From This Phase

- **A multi-phase design decision paying off.** `Constraints.priority`
  was made `Optional` back in the Phase 4→5 conversation specifically so
  *this* phase would own the "no preference stated" default. That's
  exactly what `resolve_priority()` does — and it's the only place in
  the codebase that does it.
- **Contracts constrain design, and that's a feature.** Phase 0's
  `RankedResult` wraps one `NormalizedProduct`, not a basket — that
  single fact determined this entire phase ranks per-product rather than
  trying to pick one best store for a whole order. Respecting an
  existing contract sometimes means resisting an intuitively "nicer"
  design.
- **Hard constraints vs. soft scoring are different operations.** A
  stated limit ("under 20 minutes") filters candidates out entirely; a
  preference ("cheapest") only orders what's left. Conflating them would
  let a violating result still appear, just ranked lower — wrong.
- **Structural enforcement beats trusting a docstring.** "Never use an
  LLM" is backed by an actual test that parses `ranking.py`'s AST and
  asserts no `app.core.llm`/`app.agents` import exists — a rule that
  can't silently rot as the codebase grows.

---

## 3. Architecture Fit

Implements `processing/ranking.py` from Phase 0 §2/§5.2/§9/§11. Depends
only on `domain/` (`Constraints`, `Priority`, `NormalizedProduct`,
`RankedResult`) — zero dependency on `core/llm/`, `agents/`,
`automation/`, or `adapters/`, verified both by inspection and by an
executable test. Not wired into `graph/`, consistent with Phases 7–10.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/domain/
└── ranked_result.py   **RankedResult**

backend/app/processing/
└── ranking.py            **resolve_priority, apply_hard_constraints, rank_products_for_one_item, rank_search_results, RankingSummary**

backend/tests/domain/
└── test_ranked_result.py   **new**

backend/tests/processing/
└── test_ranking.py           **new**
```

---

## 5. File-by-File Explanation

### `app/domain/ranked_result.py`
`RankedResult` — `product` (a `NormalizedProduct`), `rank` (≥1),
`score` (lower is always better, regardless of which priority mode
produced it — keeps sorting logic uniform), `rationale` (set only for
rank 1).

### `app/processing/ranking.py`

**`resolve_priority(priority)`** — `None → Priority.BEST_VALUE`. The
single consumer of the nullability introduced back in Phase 4→5.

**`apply_hard_constraints(products, constraints)`** — filters (never
scores) by `in_stock`, `max_delivery_minutes`, `max_budget`. Returns
both the survivors and a count of what got excluded, so callers can
report "3 options didn't meet your delivery-time limit" rather than
silently vanishing them.

**`_min_max_normalize(values)`** — scales a list to `[0, 1]`; all-equal
input scales to all-zero (no penalty on a dimension with no real
variation, rather than a divide-by-zero).

**`_score_products(products, priority)`** — `CHEAPEST` → raw price;
`FASTEST` → raw ETA; `BEST_VALUE` → equal-weighted average of
normalized price and normalized ETA. Verified with a deliberately
symmetric tradeoff case (cheap-but-slow vs. pricey-but-fast) landing at
identical scores (0.5/0.5) — confirming the formula doesn't secretly
favor either dimension.

**`_rationale_for(...)`** — a plain f-string template, only for rank 1.
Explicitly not LLM-generated; Phase 12 owns the real natural-language
explanation.

**`rank_products_for_one_item`** / **`rank_search_results`** — the
per-product ranking function and the full entry point that groups a
mixed product list by `product_name` first. Grouping is safe to do
directly on the string, since Phase 10 already guarantees consistent
trim+lowercase normalization across every store's results.

---

## 6. Manual Testing & Verification

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/domain/test_ranked_result.py tests/processing/test_ranking.py -v
```

**Expected:** 19 tests pass (3 domain + 16 processing).

### Optional: exercise it directly

```python
from app.processing.ranking import rank_search_results
from app.domain.constraints import Constraints, Priority
from app.domain.normalized_product import NormalizedProduct

products = [
    NormalizedProduct(store_id="zepto", product_name="onion", price_inr=10, eta_minutes=20, quantity=1, unit="kg"),
    NormalizedProduct(store_id="blinkit", product_name="onion", price_inr=15, eta_minutes=10, quantity=1, unit="kg"),
]
summary = rank_search_results(products, Constraints(priority=Priority.CHEAPEST))
for name, ranked in summary.rankings.items():
    for r in ranked:
        print(name, r.rank, r.product.store_id, r.score, r.rationale)
```

**Expected:** `onion 1 zepto 10.0 'Cheapest option: ₹10.00'` then
`onion 2 blinkit 15.0 None`.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| Everything comes back with an empty ranked list for a product | All candidates were filtered by a hard constraint | Check `RankingSummary.excluded_counts[product_name]` — a nonzero count with an empty ranking means the constraint, not a bug, is the cause. |
| `best_value` ranking looks identical to `cheapest` | Every candidate has the same ETA (so `eta_norm` contributes nothing, and the score is dominated by price alone) | Expected behavior of `_min_max_normalize` on constant input — not a bug. |
| `rationale` is `None` for a result you expected to have one | It isn't rank 1 | By design — only the top pick gets a rationale. |

---

## 8. Edge Cases Considered

- **All candidates filtered out** — returns an empty ranked list with a
  correct `excluded_count`, not an error (tested explicitly).
- **Symmetric price/ETA tradeoff under `best_value`** — verified to
  produce tied scores, not an arbitrary tiebreak masquerading as a real
  preference.
- **`None` priority through the full pipeline** — verified end-to-end
  via `rank_search_results`, not just at the `resolve_priority` unit level.
- **Multiple distinct products in one call** — grouped and ranked fully
  independently; a filter/constraint affecting one product's candidates
  has zero effect on another's.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/domain/test_ranked_result.py tests/processing/test_ranking.py -v` — 19/19 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).
- [ ] `test_ranking_never_imports_the_llm_layer` passes (structural, not just documented).

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] Full runtime verification in this sandbox: priority resolution,
      every constraint-filter combination (delivery time, budget,
      in_stock, and all three combined), min-max normalization (equal
      and varied inputs), scoring for all three priority modes, ranking
      order for cheapest/fastest, rationale-only-on-rank-1, all-filtered-
      out handling, and the full multi-product `rank_search_results`
      integration including the `None → BEST_VALUE` end-to-end path.
- [x] Zero dependency on `core/llm/`/`agents/` — verified both by
      inspection and by an AST-parsing test that fails loudly if this
      is ever violated.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- `best_value`'s equal weighting (50/50 price/ETA) is a defensible
  neutral default, not empirically tuned — there's no real user data
  yet to justify skewing either direction.
- Ranking is per-product, not per-basket (§2) — there is currently no
  "which single store is best for my whole order" answer; that's
  explicitly deferred to Phase 12.
- Ties (identical scores) are broken by Python's stable sort — whichever
  candidate appeared first in the input list wins a tie. Not currently
  documented as a deliberate policy beyond "stable and deterministic,"
  since there's no principled tiebreak rule to apply yet.

## 12. Improvements to Consider Later

- Once Phase 12 (Recommendation Generation) exists, revisit whether it
  should aggregate per-product rankings into a single store-level
  recommendation, or present per-item best-options directly to the user.
- If real usage shows `best_value`'s 50/50 weighting doesn't match user
  expectations, make the weights configurable rather than hardcoded —
  not justified to build now without evidence it's needed.

---

## Next Step

Once `pytest tests/domain/test_ranked_result.py tests/processing/test_ranking.py -v`
passes locally (19/19), say **"Move to Phase 12"** to build the
Recommendation Generator — the first LLM-backed component since Phase 4,
producing a natural-language explanation of the ranked results.
