# Phase 10 — Normalization Layer

> **Status:** Maps Phase 9-verified raw results into the fully-typed
> `NormalizedProduct` schema. Standalone, not wired into Phase 5's graph.
> Master's instruction for this phase: "Explain every normalization
> rule" — §5 does exactly that, rule by rule.

---

## 1. Goal

Turn string-typed `RawProductResult` data into `NormalizedProduct` — the
common, fully-typed schema Ranking (Phase 11), Recommendation Generation
(Phase 12), and Order Execution (Phase 14) will all consume, regardless
of which store or which raw scraping format produced the underlying data.

---

## 2. Concepts to Learn From This Phase

- **All-or-nothing normalization per item.** A record with a good price
  but an unparseable quantity isn't "half normalized" with a fabricated
  quantity — the whole item is dropped and reported. Partial correctness
  is worse than an honest gap.
- **Compound unit parsing is a genuine correctness trap.** "1 hr 30 mins"
  naively parsed (take all numbers, multiply by 60 if "hr" appears
  anywhere) gives 1800 minutes, not 90. Getting this right required
  separating hour and minute extraction into independent regex passes.
- **Deliberately scoping out unit canonicalization.** Extracting "500g"
  as `(500.0, "g")` rather than converting to `(0.5, "kg")` is a real,
  documented scope decision — not an oversight — because canonicalizing
  correctly requires knowing every unit variant real stores actually use,
  which isn't knowable without real data (same category of honesty as
  Phase 8's locator placeholders).
- **Reuse over reimplementation.** Price parsing isn't rewritten here —
  it imports Phase 9's `parse_price()` directly.

---

## 3. Architecture Fit

Implements `processing/normalization.py` from Phase 0 §2/§5.2/§9 — pure
deterministic Python, zero LLM, zero Appium dependency. `NormalizedProduct`
is promoted to `app/domain/` (same precedent as `RawProductResult` in
Phase 7) since Phase 0 §11 fully specs it as a genuine cross-phase
contract. Not wired into `graph/` — consistent with Phases 7, 8, 9.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/domain/
└── normalized_product.py   **NormalizedProduct**

backend/app/processing/
└── normalization.py          **NormalizationIssue, NormalizationResult, normalize_verified_results() + 3 parsers**

backend/tests/domain/
└── test_normalized_product.py   **new**

backend/tests/processing/
└── test_normalization.py          **new**
```

No DI factory added — same reasoning as Phase 9 (pure functions, no
state to inject).

---

## 5. Every Normalization Rule, Explained

This is the section master's instructions specifically asked for.

### Rule 1 — Title: trim + lowercase
`"  Onion  "` → `"onion"`. Identical convention to `ProductRequest.name`
(Phase 4), deliberately — so a normalized result's name and the user's
originally-requested product name are always directly comparable without
re-normalizing either side.

### Rule 2 — Price: reuse Phase 9's `parse_price()`
No new logic — imported directly. Strips currency symbols/commas, must
parse to a positive float. Guarantees identical behavior between
Verification and Normalization; changing price-parsing rules only ever
requires touching one function.

### Rule 3 — ETA: separate hour/minute extraction, then combine
`parse_eta_minutes()` runs two independent regex passes — one for
`(\d+)\s*(?:hr|hour)`, one for `(\d+)\s*(?:min)` — then computes
`hours * 60 + minutes`. This is what correctly handles compound values:

| Input | Naive (wrong) result | This function's (correct) result |
|---|---|---|
| `"1 hr 30 mins"` | 1800 (treats the 30 as also being hours) | **90** |
| `"2 hrs 15 min"` | 900 | **135** |
| `"15 mins"` | 15 | 15 |
| `"1 hr"` | 60 | 60 |

**Range handling:** `"15-20 mins"` → **20** (upper bound). When only one
number in a range is immediately adjacent to the unit word (as regex
matching naturally produces here), that's the number taken — which
happens to always be the range's upper bound in the observed formats.
Documented as deliberate, not coincidental: promising the shorter time
and being wrong is worse for user trust than the reverse.

Unparseable text (`"just now"`, `"asap"`, empty string) → `None`, never a
guessed value.

### Rule 4 — Quantity: extract, don't canonicalize
`parse_quantity()` finds the first `<number><unit>` pattern:
`"1 kg"` → `(1.0, "kg")`, `"500g"` → `(500.0, "g")`,
`"2 pcs"` → `(2.0, "pcs")`. **Deliberately does not convert units** — "g"
stays "g", not converted to "0.5 kg". Real store apps' full range of unit
conventions isn't knowable without real data (Phase 8's placeholder-
locator situation applies here too, in spirit) — canonicalizing
incorrectly would be worse than not canonicalizing at all. Flagged
explicitly in §11 as a scoped-out future improvement, not an oversight.

### Rule 5 — `in_stock`: always `True`, an honest placeholder
`RawProductResult` (Phase 0's own spec) has no stock-status field.
There's no real signal to derive this from yet — defaulting to `True`
and saying so plainly beats pretending to infer something that isn't
there.

### Rule 6 — All-or-nothing per item
If price, ETA, *or* quantity fails to parse, the entire item is dropped
— never partially normalized with a fabricated value for the field that
failed. Every drop is reported as a `NormalizationIssue` with the exact
reason, mirroring Phase 9's "never silently discard" precedent.

---

## 6. Manual Testing & Verification

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/domain/test_normalized_product.py tests/processing/test_normalization.py -v
```

**Expected:** 34 tests pass (12 domain + 22 processing).

### Optional: exercise it directly

```python
from app.processing.normalization import normalize_verified_results
from app.domain.raw_product_result import RawProductResult

results = [
    RawProductResult(store_id="zepto", raw_title="Onion", raw_price="42.00", raw_eta="15 mins", raw_quantity="1 kg"),
    RawProductResult(store_id="zepto", raw_title="Curd", raw_price="30.00", raw_eta="1 hr 30 mins", raw_quantity="500 g"),
]
result = normalize_verified_results(results)
for p in result.normalized_products:
    print(p.model_dump_json())
```

**Expected:** two `NormalizedProduct` lines, the second showing
`"eta_minutes": 90` (not 1800 or 30) — the compound-parsing correctness
check made visible.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| A product you expected to see is missing from `normalized_products` | One of its raw fields failed to parse | Check `result.issues` — every drop is reported with the specific field and raw value that failed. |
| ETA looks wildly wrong (e.g. thousands of minutes) | A new raw format not covered by the hour/minute regex, or a genuine bug reintroduced in the compound-parsing logic | Re-run the exact test matrix in `test_parse_eta_minutes_valid_formats` — if all those pass, the issue is a new format, not a regression. |
| Quantity unit looks "wrong" (e.g. shows "g" when you expected "kg") | Expected — Rule 4 deliberately doesn't canonicalize units | Not a bug; see §5 Rule 4 and §11. |

---

## 8. Edge Cases Considered

- **Empty input list** — returns an empty `NormalizationResult`, no crash.
- **Item with ALL THREE fields unparseable** — still just one issue
  entry per item (all problems joined into a single `detail` string),
  not three separate issues for one item.
- **Range with no unit word at all** (e.g. `"15-20"`) — falls back to
  the bare-number pattern, still takes the upper bound.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/domain/test_normalized_product.py tests/processing/test_normalization.py -v` — 34/34 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).
- [ ] `grep -r "ollama\|appium\|selenium" app/processing/normalization.py` — no output.

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] Full runtime verification in this sandbox: every ETA format
      (including the compound "1 hr 30 mins" → 90 case specifically,
      which a naive parser would get wrong), every quantity format,
      title normalization, and the full integrated scenario with mixed
      valid/malformed items — all confirmed correct, including the
      all-or-nothing single-bad-field-drops-whole-item behavior.
- [x] Zero dependency on `agents/`, `core/llm/`, `automation/`, or
      `adapters/` — only `domain/` and Phase 9's `processing/verification.py`.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- **No unit canonicalization** (§5 Rule 4) — "500g" and "0.5kg" are
  treated as different units, not recognized as equivalent quantities.
  Real store data is needed to build a correct, complete conversion
  table; guessing one now risks silent wrong conversions, worse than no
  conversion at all.
- **`in_stock` is always `True`** — no real signal exists yet in
  `RawProductResult` to derive this from.
- **ETA regex is tuned to the formats I could reasonably anticipate**
  ("X mins", "X hr Y mins", ranges) — a genuinely novel format from a
  real store (once real locators exist, Phase 8) may need a new pattern
  added to `_HOUR_PATTERN`/`_MINUTE_PATTERN`.
- Not wired into the LangGraph workflow, by design (§3).

## 12. Improvements to Consider Later

- Build a real unit-canonicalization table once actual store data
  reveals which unit variants genuinely appear (g/kg, ml/l, pc/pcs/unit,
  etc.) — premature to guess now.
- If a real store app exposes an explicit "out of stock" UI element,
  extend `RawProductResult`/`StoreLocatorConfig` (Phase 8) to capture it,
  then remove the `in_stock=True` placeholder here.

---

## Next Step

Once `pytest tests/domain/test_normalized_product.py tests/processing/test_normalization.py -v`
passes locally (34/34), say **"Move to Phase 11"** to build the Ranking
Engine — deterministic ranking by cheapest/fastest/best-value, the layer
that finally puts `Constraints.priority` (made nullable back in the
Phase 4→5 deferred fix) to real use.
