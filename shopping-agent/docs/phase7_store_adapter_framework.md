# Phase 7 — Store Adapter Framework

> **Status:** Full `StoreAdapter` interface + 3 concrete mock adapters
> (Zepto, Blinkit, Instamart). All data mocked, deterministic, no Appium.
> **Not wired into the Phase 5 graph** — see §0 for why, and what that
> means for Phase 8.

---

## 0. Why this phase does NOT touch the LangGraph workflow

Phase 5's `tool_orchestration_node` currently uses its own private mock
(`app/graph/mocks.py`), producing a float-typed `MockProductResult`
(`price_inr: float`). This phase's real `RawProductResult` (per Phase 0
§11) is deliberately **string-typed** (`raw_price: str`) — it represents
scraped data exactly as observed, before any parsing. Turning those
strings into real numbers is explicitly Phase 9's job (Verification
Layer), not this one's.

Wiring the new adapters into the graph *now* would force a choice between
building Phase 9's real parsing early (jumping ahead, against master rule
#8 in spirit and the explicit "never jump ahead" final rule) or breaking
Phase 5's 40 passing graph tests. Neither is right. The master plan's own
structure — a full "Phase 15: Integration Testing... connect all
modules" — implies each of Phases 6–14 builds a standalone, fully tested
layer, with Phase 15 as the deliberate integration point. This phase
follows that structure: **Phase 5's graph and its tests are completely
untouched.**

---

## 1. Goal

Build the real `StoreAdapter` interface from Phase 0 §6, plus three named
concrete implementations, all still returning deterministic mocked
data — proving the interface itself is sound and uniformly implementable
before Phase 8 wires any of them to real Appium sessions.

---

## 2. Concepts to Learn From This Phase

- **`Protocol` + `@runtime_checkable`** — how this gives you a genuine
  `isinstance()` conformance check, not just a static-analysis hint.
- **Interface contract tests** — one parametrized test suite run against
  every implementation, versus N near-duplicate test files. This is
  exactly what "every adapter must expose the same interface" (master
  rule #6) looks like as *executable proof*, not just a docstring claim.
- **"Raw" vs. "parsed" data as a deliberate pipeline boundary** — why
  `RawProductResult` is string-typed on purpose, and why that boundary
  matters for keeping phases genuinely independent.
- **Provisional interfaces** — `CartActionResult`/`CheckoutState` are
  explicitly flagged as "good enough for now, will be revisited" rather
  than pretending they're final. Recognizing which decisions are
  load-bearing (the `StoreAdapter` method signatures) vs. which are
  placeholders (their exact return shapes) is a real design skill.

---

## 3. Architecture Fit

Implements `adapters/` from Phase 0 §2/§6/§9. Dependency direction
verified by inspection: `adapters/` depends on `domain/` only — nothing
in `app/adapters/` imports from `graph/`, `automation/`, `agents/`, or
`api/`. This matters specifically because it would have been easy (and
wrong) to reach for Phase 5's `app.graph.mocks` for pricing logic — the
Phase 0 dependency graph only allows `graph/`/`services/` to depend on
`adapters/`, never the reverse.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/domain/
└── raw_product_result.py   **RawProductResult — new domain contract**

backend/app/adapters/
├── base.py                   **StoreAdapter (runtime_checkable Protocol)**
├── types.py                    **SearchQuery, CartActionResult, CheckoutState**
├── _mock_data.py                 **shared DRY mock-generation helper**
├── zepto/adapter.py                **ZeptoAdapter**
├── blinkit/adapter.py                **BlinkitAdapter**
└── instamart/adapter.py                **InstamartAdapter**

backend/tests/domain/
└── test_raw_product_result.py    **new**

backend/tests/adapters/
├── test_types.py                   **new**
├── test_adapter_contract.py          **new — parametrized across all 3 adapters**
└── test_store_specific_behavior.py     **new**
```

`app/core/dependencies.py` gets 4 new factories: `get_zepto_adapter()`,
`get_blinkit_adapter()`, `get_instamart_adapter()`,
`get_all_store_adapters()`.

---

## 5. File-by-File Explanation

### `app/domain/raw_product_result.py`
`RawProductResult` — `store_id`, `raw_title`, `raw_price`, `raw_eta`,
`raw_quantity` (all `str`), `screenshot_ref` (optional). Every numeric-
looking field is deliberately a string: this is the exact shape Phase 0
§11 specified for data straight off a store's UI, before any validation.

### `app/adapters/types.py`
`SearchQuery` (a thin wrapper around `list[ProductRequest]`, leaving room
to add search-scoped options later without touching every adapter's
signature), `CartActionResult`, `CheckoutState` — both explicitly
documented as provisional, since Phase 0 didn't field-spec them in detail
and Phase 14 will design the real cart/checkout flow.

### `app/adapters/base.py`
`StoreAdapter` — a `@runtime_checkable Protocol` with five methods:
`get_store_id`, `is_available`, `search`, `add_to_cart`, `checkout`. No
shared implementation (matches Phase 0 §6's explicit "interface, not a
base class with shared implementation" design note). `runtime_checkable`
means `isinstance(adapter, StoreAdapter)` is a real, executable
conformance check — used directly in the contract test suite.

### `app/adapters/_mock_data.py`
Private (leading underscore) shared helper — `generate_mock_results()`,
`mock_add_to_cart()`, `mock_checkout()`. Exists purely for DRY: three
adapters would otherwise reimplement an identical pricing formula.
Deliberately does **not** import from `app.graph.mocks`, even though the
spirit is similar — see §0/§3 on why that dependency direction is wrong.

### `app/adapters/{zepto,blinkit,instamart}/adapter.py`
Three thin classes, each ~20 lines: a `STORE_ID` constant, a
`_PRICE_OFFSET`/`_ETA_MINUTES` pair (arbitrary but fixed — Zepto
cheapest/fastest, Blinkit priciest/slowest, Instamart in between), and
five one-line methods delegating to `_mock_data.py`. Every store's mock
pricing genuinely differs, verified explicitly
(`test_stores_produce_meaningfully_different_prices_for_the_same_request`)
so a future real Ranking Engine (Phase 11) will have something meaningful
to sort even while everything's still mocked.

---

## 6. Manual Testing & Verification

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/domain/test_raw_product_result.py tests/adapters/ -v
```

**Expected:** 32 tests pass (7 + 4 + 21 — the contract suite has 7
parametrized test functions × 3 adapters = 21, plus 4 store-specific + 7
raw-result domain tests).

### Optional: exercise the adapters directly

```python
# From backend/, venv active: python3
from app.core.dependencies import get_all_store_adapters
from app.adapters.types import SearchQuery
from app.domain.product import ProductRequest

adapters = get_all_store_adapters()
query = SearchQuery(products=[ProductRequest(name="onion"), ProductRequest(name="curd")])

for adapter in adapters:
    print(adapter.get_store_id(), "->", [(r.raw_title, r.raw_price) for r in adapter.search(query)])
```

**Expected:** three lines, one per store, each showing 2 products with
different prices per store.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `isinstance(adapter, StoreAdapter)` returns `False` for a new adapter you write | Missing one of the five required methods, or a typo in a method name | `Protocol` conformance is structural — the method set must match exactly; check spelling against `app/adapters/base.py`. |
| Two stores return identical prices | `_PRICE_OFFSET` values collided | Check each adapter's module-level constants are distinct. |
| `ValidationError` constructing `RawProductResult` | Passed an empty string for a required field | Every string field has `min_length=1` — mock data generation should never produce blanks; check `_mock_data.py` if it does. |

---

## 8. Edge Cases Considered

- **Multi-product search** — each product gets its own price based on
  position in the list, not a flat per-store price — verified
  (`test_search_returns_one_result_per_product_stamped_with_store_id`).
- **Repeated search calls** — fully deterministic, no randomness
  anywhere, verified explicitly for ranking-test reproducibility later.
- **`add_to_cart` given a result from a *different* store than the
  adapter it's called on** — not currently guarded against (the mock
  just stamps whatever `store_id` the adapter itself has, ignoring the
  input result's own `store_id`). Flagged as a known limitation, not a
  bug worth fixing in a mock — real Phase 8 automation would naturally
  fail here since it'd be trying to click on the wrong app's cart button.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/domain/test_raw_product_result.py tests/adapters/ -v` — 32/32 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 pass (proof this phase changed nothing in `graph/`).
- [ ] `grep -r "from app.graph" app/adapters/` — no output (adapters never import from graph).

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] Full runtime verification in this sandbox (offline pydantic stub,
      same technique as every prior phase): Protocol conformance via
      `isinstance`, store IDs, `is_available`, multi-product search
      shape and store-stamping, determinism across calls, distinct
      pricing across all 3 stores (`zepto: 10.00`, `blinkit: 15.00`,
      `instamart: 12.50` — confirmed genuinely different), `add_to_cart`/
      `checkout` return types and stamping, and raw-field parseability.
- [x] Zero dependency from `adapters/` into `graph/`, `automation/`,
      `agents/`, or `api/` — verified by inspection of every import.
- [x] `app/graph/` untouched — Phase 5's 40 tests remain exactly as they were.

---

## 11. Known Limitations

- Not wired into the LangGraph workflow — by design (§0), not an oversight.
- `add_to_cart` doesn't validate that the given `RawProductResult` actually
  belongs to the adapter it's called on (see §8).
- `CartActionResult`/`CheckoutState` are provisional shapes — Phase 14
  will likely need to redesign them once real add-to-cart/checkout flows
  reveal what data actually matters (order IDs, cart totals, etc.).
- `add_to_cart`'s parameter type (`RawProductResult`) is a stand-in for
  what should probably eventually be `NormalizedProduct` or `RankedResult`
  — flagged in `base.py`'s own docstring, to be revisited once those
  types exist (Phase 10/11).

## 12. Improvements to Consider Later

- Once Phase 8 gives adapters real `DriverManager` sessions,
  `get_all_store_adapters()`'s `@lru_cache` singleton caching needs
  revisiting — a live Appium session shouldn't be silently shared/reused
  the way a stateless mock safely can be.
- Consider a lightweight `store_id` cross-check in `add_to_cart` once real
  automation exists, so a mismatched call fails fast with a clear error
  instead of silently doing the wrong thing.

---

## Next Step

Once `pytest tests/domain/test_raw_product_result.py tests/adapters/ tests/graph/ -v`
all pass locally, say **"Move to Phase 8"** to begin Real Appium
Automation — connecting these adapters to actual Appium sessions (open
app, search product, read prices/ETA/quantities) using the `DriverManager`
and wait/gesture primitives built in Phase 6.
