# Phase 9 — Verification Layer

> **Status:** Deterministic validation of raw search results — invalid
> prices, duplicates, missing products, and a retry-decision signal for
> unresponsive stores. Standalone, not wired into Phase 5's graph.

---

## 1. Goal

Take the `list[RawProductResult]` that Phase 7/8's adapters produce (or
would produce, once real locators exist) and determine what's actually
usable — rejecting malformed prices, deduplicating same-store repeats,
and flagging what's missing entirely — exactly the five things master's
phase plan names for this phase, no more, no less.

---

## 2. Concepts to Learn From This Phase

- **Pipeline order can change correctness, not just style.** Running
  price validation before duplicate detection isn't arbitrary — it
  determines *which* of two duplicate entries survives when they differ
  in validity. Tested explicitly
  (`test_price_validation_before_dedup_keeps_the_valid_duplicate`).
- **Same-store vs. cross-store duplication are different concepts.** The
  same product appearing once per store is the entire point of this
  system; the same product appearing twice *from the same store* is a
  scraping glitch. Conflating them would break Ranking before it's even
  built.
- **A "decision signal" vs. a "mechanism".** `stores_needing_retry`
  answers *which* stores look like they need retrying; it doesn't *do*
  the retrying — that's Phase 5's already-built `retry_orchestration`
  loop. Recognizing which phase owns the decision vs. the execution is a
  real architectural skill.

---

## 3. Architecture Fit

Implements `processing/verification.py` from Phase 0 §2/§5.2/§9 — pure
deterministic Python, zero LLM, zero Appium dependency. Depends only on
`domain/` (`ProductRequest`, `RawProductResult`), matching the Phase 0
dependency graph exactly. Not wired into `graph/` — same reasoning
established in Phases 7 and 8 (Phase 15 is the integration point).

---

## 4. Folder Structure (this phase's addition in bold)

```
backend/app/processing/
└── verification.py   **VerificationIssue, VerificationResult, verify_search_results() + 5 helper functions**

backend/tests/processing/
└── test_verification.py   **new**
```

No DI factory added — every function here is pure (no state, no
injected dependencies), so callers just import directly; wrapping
stateless functions in a DI factory would be pure ceremony (rule #8:
avoid overengineering).

---

## 5. File-by-File Explanation

### `app/processing/verification.py`

**`parse_price(raw_price)`** — strips common currency noise (`₹`, `Rs.`,
`Rs`, `INR`, `$`, thousands-separator commas), attempts a float
conversion, and rejects anything `<= 0`. Never raises — returns `None`
for anything unusable, letting callers decide what to do about it.

**`verify_prices`** / **`detect_duplicates`** / **`detect_missing_products`**
/ **`detect_stores_needing_retry`** — four small, independently-tested
pure functions, each doing exactly one of master's five named checks
("failed automation" is covered by `detect_stores_needing_retry`: a store
that returned literally nothing valid is exactly what a failed
automation attempt looks like from this layer's perspective).

**`verify_search_results`** — the single entry point, composing all four
in the deliberate order described in §2. Returns a `VerificationResult`:
`valid_results` (what survived), `issues` (a structured, typed audit
trail of everything that didn't — never a silent drop), `missing_products`,
`stores_needing_retry`.

---

## 6. Manual Testing & Verification

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/processing/ -v
```

**Expected:** 20 tests pass (accounting for the two 5-case parametrized
`parse_price` tests: 12 test functions, 2 of which each run 5 times).

### Optional: exercise it directly

```python
from app.processing.verification import verify_search_results
from app.domain.product import ProductRequest
from app.domain.raw_product_result import RawProductResult

requested = [ProductRequest(name="onion"), ProductRequest(name="milk")]
raw = [
    RawProductResult(store_id="zepto", raw_title="onion", raw_price="42.00", raw_eta="15 mins", raw_quantity="1 kg"),
    RawProductResult(store_id="zepto", raw_title="onion", raw_price="43.00", raw_eta="15 mins", raw_quantity="1 kg"),
]
result = verify_search_results(requested, ["zepto", "blinkit"], raw)
print(result.model_dump_json(indent=2))
```

**Expected:** one valid result (the first onion), one `duplicate` issue,
`missing_products: ["milk"]`, `stores_needing_retry: ["blinkit"]`.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| A price you know is valid gets rejected | Currency symbol/format not in `_CURRENCY_NOISE` (e.g. a store using a different separator style) | Add the new noise pattern to `_CURRENCY_NOISE` in `verification.py`. |
| A product incorrectly shows as "missing" | The store's `raw_title` doesn't literally contain the requested product name as a substring (e.g. a synonym or translation) | Same conservative-matching tradeoff as Phase 4's `_filter_unsupported_products` — documented, not a bug. |
| A store shows as needing retry even though it had SOME results | All of that store's results were rejected upstream (invalid price or all duplicates) | Check `issues` for that store's specific rejection reasons — `stores_needing_retry` reflects post-validation state, not raw result count. |

---

## 8. Edge Cases Considered

- **Empty `raw_results`** — every requested product is reported missing,
  every attempted store needs retry; no crash (all four helper functions
  handle empty lists naturally via their loop-based implementations).
- **A store contributes results, but all get rejected** (e.g. all
  invalid prices) — correctly flagged for retry, since the *valid*
  result count for that store is what matters, not the raw count.
- **Duplicate detection interacting with invalid prices** — the
  explicitly tested ordering case: an invalid-priced "first occurrence"
  must not survive over a later, valid-priced duplicate.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/processing/ -v` — 20/20 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).
- [ ] `grep -r "ollama\|appium\|selenium" app/processing/verification.py` — no output (zero LLM/Appium dependency, verified).

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] Full runtime verification in this sandbox (offline pydantic stub):
      every `parse_price` case (5 valid formats, 5 invalid), price
      filtering, same-store vs. cross-store duplicate handling, the
      ordering-sensitive validate-before-dedup case, missing-product
      detection, retry-store detection, and the full integrated
      `verify_search_results` scenario — all confirmed correct.
- [x] Zero dependency on `agents/`, `core/llm/`, `automation/`, or
      `adapters/` — verified by inspection; only imports from `domain/`.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- Missing-product detection uses simple substring matching, same
  documented tradeoff as Phase 4 — a synonym or translated product name
  would be conservatively (and safely) reported as "missing" rather than
  matched.
- `_CURRENCY_NOISE` is a small, hardcoded list — real store apps may use
  formats not yet seen (e.g. a space-separated thousands format);
  extend as real data reveals gaps, per §7's debugging guide.
- Not wired into the LangGraph workflow, by design (§3), not oversight.

## 12. Improvements to Consider Later

- If real automation (once real locators exist, per Phase 8) reveals
  price formats this layer doesn't handle, extend `_CURRENCY_NOISE`
  rather than adding format-specific branches — keep `parse_price` a
  single, simple normalization pass.
- Consider whether `missing_products`/`stores_needing_retry` should
  eventually feed into the Recommendation Generator (Phase 12) as
  user-facing "we couldn't find X" messaging — not needed until that
  phase exists.

---

## Next Step

Once `pytest tests/processing/ -v` passes locally (20/20), say
**"Move to Phase 10"** to build the Normalization Layer — mapping each
store's now-verified but still string-typed results into the common,
fully-typed `NormalizedProduct` schema every downstream phase (Ranking,
Recommendation) will consume.
