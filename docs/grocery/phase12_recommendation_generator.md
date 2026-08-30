# Phase 12 — Recommendation Generator

> **Status:** First LLM-backed component since Phase 4. Deterministic
> basket selection (Python) decides WHICH store; the LLM only explains
> WHY, with its output fact-checked and a safe template fallback.

---

## 1. Goal

Close the gap Phase 11 explicitly left open (ranking is per-product, a
recommendation needs to be per-store) with deterministic Python, then
generate a natural-language explanation of that already-made choice using
the LLM — applying every lesson learned from Phase 4's two hardening
rounds to this new LLM-backed component.

---

## 2. Concepts to Learn From This Phase

- **The LLM explains a decision, it never makes one.** `select_best_store`
  (pure Python) picks the store before `RecommendationGenerator` is ever
  called. The LLM sees only already-decided facts and phrases them —
  structurally impossible for it to recommend a different store, because
  it's never asked to choose.
- **Fact-checking generated text is possible, just different from
  fact-checking extracted data.** Phase 4 checked "does this product name
  appear in the input" (extraction). This phase checks "does this store
  name and this exact price appear in the output" (generation) — same
  substring-verification instinct, applied in the opposite direction.
- **A deterministic fallback template is a real safety net, not a cop-out.**
  When the LLM's output can't be verified, the system doesn't error out
  or ship something unverifiable — it falls back to a plain but
  100%-accurate template. This is also directly testable, independent of
  the LLM ever running.
- **Backward-compatible refactoring.** Promoting `min_max_normalize` out
  of `ranking.py` into a shared module, while keeping the old private
  name working exactly as before, is what "never break previous-phase
  functionality" looks like in practice when new code genuinely needs to
  reuse old logic.

---

## 3. Architecture Fit

Two new files, matching the established reasoning/deterministic split:
`app/processing/recommendation_selection.py` (deterministic — depends
only on `domain/` and `processing/ranking.py`) and
`app/agents/recommendation_agent.py` (LLM-backed — depends on
`core/llm/` and the selection module's output type, mirroring
`intent_agent.py`'s shape exactly). Not wired into `graph/`, consistent
with Phases 7–11.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/processing/
├── _scoring_utils.py                 **new — shared min_max_normalize()**
├── ranking.py                          *(edited: imports the shared utility, old private name preserved)*
└── recommendation_selection.py       **new — StoreBasketSummary, select_best_store()**

backend/app/agents/
└── recommendation_agent.py           **new — RecommendationGenerator**

backend/app/core/llm/prompt_templates/
└── recommendation_explanation.txt    **new**

backend/tests/processing/
├── test_scoring_utils.py             **new**
└── test_recommendation_selection.py  **new**

backend/tests/agents/
└── test_recommendation_agent.py      **new**
```

`app/core/dependencies.py` gets `get_recommendation_generator()`.

---

## 5. File-by-File Explanation

### `app/processing/_scoring_utils.py`
`min_max_normalize()` — extracted verbatim from Phase 11's `ranking.py`.
Backward-compatible: `ranking.py` now imports it and re-exports it under
its old private name, so Phase 11's existing code and tests are
completely unaffected — verified by re-running the exact assertions from
Phase 11's verification against the refactored module.

### `app/processing/recommendation_selection.py`
`select_best_store(ranking_summary)` — the aggregation Phase 11 deferred.
For every store appearing anywhere in the per-product rankings, builds a
`StoreBasketSummary` (total price, worst-case ETA, which requested
products it has/lacks). Selection policy, in order: **completeness
first** (fewest missing products always wins, regardless of price/speed
— verified explicitly with a case where a complete-but-pricier store
beats an incomplete-but-cheaper one), then priority-based scoring among
equally-complete stores, using the same `min_max_normalize` formula
Phase 11 uses for `best_value`. Returns `None` if nothing survived
Ranking's constraints for any product at all.

### `app/agents/recommendation_agent.py`
`_ExplanationOutput` — single required `explanation` field, no
Optional/nullable trap possible (Phase 4 Incident 1's lesson, applied
here even though there's only one field). `_fallback_explanation` — a
plain f-string template per priority mode, mentioning missing products
honestly when relevant. `_explanation_mentions_key_facts` — the fact
check: store name and exact formatted price must both appear in the
LLM's text. `RecommendationGenerator.generate()`: skips the LLM entirely
when `basket is None`; on an `LLMConnectionError`/`LLMValidationError`
OR a failed fact-check, falls back to the deterministic template rather
than surfacing an error or shipping unverified text.

### `app/core/llm/prompt_templates/recommendation_explanation.txt`
Gives the LLM only the already-decided facts (store, price, ETA,
matched/missing products) and explicitly instructs it not to invent
anything or recommend a different store — the prompt-level half of the
same defense-in-depth pattern established in Phase 4.

---

## 6. Manual Testing & Verification

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/processing/test_scoring_utils.py tests/processing/test_recommendation_selection.py tests/agents/test_recommendation_agent.py -v
pytest tests/processing/test_ranking.py -v   # confirm Phase 11 unaffected by the refactor
```

**Expected:** 22 new tests pass (3 + 6 + 13); Phase 11's 16 ranking tests
still pass unchanged.

### Optional: exercise it against a real Ollama model

```python
from app.core.dependencies import get_recommendation_generator
from app.processing.recommendation_selection import select_best_store
from app.processing.ranking import rank_search_results
from app.domain.constraints import Constraints, Priority
from app.domain.normalized_product import NormalizedProduct

products = [
    NormalizedProduct(store_id="zepto", product_name="onion", price_inr=10, eta_minutes=15, quantity=1, unit="kg"),
    NormalizedProduct(store_id="blinkit", product_name="onion", price_inr=15, eta_minutes=10, quantity=1, unit="kg"),
]
summary = rank_search_results(products, Constraints(priority=Priority.CHEAPEST))
basket = select_best_store(summary)
result = get_recommendation_generator().generate(basket, summary.priority_used)
print(result.explanation, "| fallback used:", result.used_fallback)
```

**Expected:** a fluent sentence mentioning Zepto and ₹10.00,
`used_fallback: False` if the model behaved; `True` (with a still-correct
templated sentence) if it didn't.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `used_fallback` is always `True` even with Ollama running | The model's phrasing doesn't include the exact price string (e.g. rounds differently, uses a different currency symbol) | Check the logged `recommendation_llm_output_failed_fact_check` warning's `raw_explanation` field to see what it actually said. |
| Explanation mentions a product that wasn't in the order | This should be structurally impossible — the prompt only lists matched/missing products from the facts given | If observed, it's evidence the fact-check needs strengthening (see §12) — the current check only verifies store+price, not full product-list fidelity. |
| `select_best_store` returns a surprising store | Check `fulfills_all_products` and `missing_products` first — completeness always wins over price/speed, which can be non-obvious | Not a bug; see §5's selection policy description. |

---

## 8. Edge Cases Considered

- **No viable basket at all** — LLM never called, deterministic message
  returned directly (tested explicitly, confirms zero LLM calls).
- **LLM output correct in spirit but missing the exact price string**
  (e.g. rounds `30.00` to `30`) — fails the fact-check by design, falls
  back rather than risk a subtly wrong number going unnoticed.
- **Every candidate basket is incomplete** — `select_best_store` still
  picks the least-incomplete one rather than returning `None`; `None` is
  reserved specifically for "nothing survived at all."

---

## 9. Acceptance Criteria

- [ ] `pytest tests/processing/test_scoring_utils.py tests/processing/test_recommendation_selection.py tests/agents/test_recommendation_agent.py -v` — 22/22 pass.
- [ ] `pytest tests/processing/test_ranking.py -v` — still 16/16 pass (refactor didn't break Phase 11).
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).

---

## 10. Verification Checklist

- [x] All new/changed files pass `py_compile`.
- [x] Refactor backward-compatibility explicitly re-verified: the old
      `app.processing.ranking._min_max_normalize` name still produces
      identical output after being changed to a re-export.
- [x] `select_best_store` runtime-verified across 6 scenarios: clear
      price winner, completeness-beats-price, partial-coverage handling,
      fastest-priority selection, empty rankings, all-filtered-out.
- [x] `RecommendationGenerator` runtime-verified end-to-end via
      `FakeLLMClient` + real `StructuredLLMService`: `basket=None` skips
      the LLM entirely, a good LLM output is used as-is, a fact-check
      failure triggers the fallback, and exhausted retries trigger the
      fallback without crashing.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- The fact-check only verifies store name + exact price — it doesn't
  confirm the LLM's mention of *which* products are included/missing is
  accurate. A model could technically get that detail wrong while still
  passing the check.
- `select_best_store`'s tie-breaking (when scores are exactly equal) uses
  Python's stable sort over `set` iteration order for store IDs, which
  isn't guaranteed deterministic across Python versions/runs in the same
  way list order is — a known, low-stakes limitation (ties are rare and
  the two candidates would be near-equally good regardless).
- No retry of the LLM call itself beyond what `StructuredLLMService`
  already does for JSON/schema validity — a failed *fact-check* goes
  straight to the fallback rather than attempting a corrective re-prompt.
  This was a deliberate simplicity choice; see §12.

## 12. Improvements to Consider Later

- If fact-check failures turn out to be common in practice, consider one
  corrective retry (similar to `StructuredLLMService`'s JSON-repair loop)
  before falling back to the template, rather than falling back
  immediately.
- Strengthen the fact-check to verify product-list fidelity, not just
  store+price, if real usage shows the LLM sometimes mentions products
  incorrectly.
- Make `select_best_store`'s store-ID iteration order deterministic
  (e.g. sort store IDs before building baskets) if tie-breaking
  reproducibility ever matters for debugging.

---

## Next Step

Once all three new test files pass locally (22/22) and Phase 11's tests
remain green (16/16), say **"Move to Phase 13"** to build the Human
Approval Flow — user confirmation, reject flow, and modify-request flow,
the deterministic layer sitting on top of this phase's recommendation.
