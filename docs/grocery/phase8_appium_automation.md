# Phase 8 — Real Appium Automation

> **Status:** Real, Appium-backed search automation — session management,
> generic search engine, per-store adapters — fully built and unit-tested
> against fakes. **Will not successfully search a real app yet** — see §0.
> `add_to_cart`/`checkout` remain unimplemented (Phase 14).

---

## 0. The central constraint of this entire phase — read this first

I have no way to know Zepto's, Blinkit's, or Instamart's actual Android
app UI element identifiers. These are proprietary, undocumented, and
change across app versions — nobody can correctly guess them without
directly inspecting the live app. So every locator value in
`app/adapters/{store}/locators.py` is an **unmistakably fake placeholder**
(`"CHANGE_ME_..."`), not a plausible-looking guess.

This matters more than it might first appear: a plausible-but-wrong guess
(e.g. a real-looking but unverified package name) risks being mistaken
for something I'd actually confirmed. An obviously-fake placeholder can't
be. This is the same principle that drove the Phase 4 anti-hallucination
work — never let fabricated data look like verified data.

**Practical consequence:** running this code against real emulators/apps
today will produce `AutomationError`s (verified in this sandbox — see
§10). That is *correct, expected* behavior for placeholder locators, not
a bug in the automation logic. Section 6 explains exactly what you need
to do (Appium Inspector) before this can search anything real.

---

## 1. Goal

Build genuine Appium-backed search automation — session lifecycle, a
generic locator-driven search engine, and three concrete adapter classes
— all correctly engineered and fully unit-tested via fakes, ready to work
the moment real locator values are supplied.

---

## 2. Concepts to Learn From This Phase

- **Structural `Protocol`s pay off across implementations, not just
  within one.** `ZeptoAppiumAdapter` satisfies the exact same
  `StoreAdapter` interface as Phase 7's `ZeptoAdapter` mock — zero
  interface changes needed for a completely different implementation.
- **Configuration over hardcoding for anything environment-specific.**
  Locators live in data (`StoreLocatorConfig`), not scattered through
  code — the automation *logic* is fully testable independent of whether
  any particular locator *value* is correct.
- **Honest incompleteness beats convenient fakery.** `add_to_cart`/
  `checkout` raise `NotImplementedError` rather than quietly returning
  mock success data — once real search results exist, nothing should be
  able to mistake a stub for the real thing.
- **Relative element lookup** (`card.find_element(...)`, scoped to an
  already-found card) vs. driver-level lookup — how Selenium/Appium scope
  searches within a subtree.

---

## 3. Architecture Fit

Implements the "connect adapters with Appium" piece of Phase 0's
architecture, sitting between `adapters/` (Phase 7) and `automation/`
(Phase 6) — exactly the dependency direction Phase 0 §9 specifies.
`app/graph/` remains completely untouched, for the same reasons
established in Phase 7 §0 (integration is Phase 15's job).

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/adapters/
├── locators.py                    **Locator config shape**
├── _appium_search.py                **generic search engine**
├── zepto/
│   ├── locators.py                    **placeholder locator values**
│   └── appium_adapter.py                **ZeptoAppiumAdapter**
├── blinkit/
│   ├── locators.py                    **placeholder locator values**
│   └── appium_adapter.py                **BlinkitAppiumAdapter**
└── instamart/
    ├── locators.py                    **placeholder locator values**
    └── appium_adapter.py                **InstamartAppiumAdapter**

backend/tests/adapters/
├── test_locators.py               **new**
├── test_appium_search.py            **new**
└── test_appium_adapters.py            **new**
```

`app/core/dependencies.py` gets 3 new factories:
`create_zepto_appium_adapter()`, `create_blinkit_appium_adapter()`,
`create_instamart_appium_adapter()` — uncached, same reasoning as
`create_driver_manager()`.

---

## 5. File-by-File Explanation

### `app/adapters/locators.py`
`SearchScreenLocators`, `ProductCardLocators`, `StoreLocatorConfig` — the
shape every store's config must satisfy. `ProductCardLocators.eta`/
`.quantity` are `Optional`, since some apps might show these once
globally rather than per result card — a real design uncertainty I can't
resolve without inspecting each app.

### `app/adapters/{store}/locators.py`
Concrete `StoreLocatorConfig` instances per store, every value an
obviously-fake `"CHANGE_ME_..."` placeholder. Extensive docstrings
explain exactly why (§0) and exactly what to do about it (§6).

### `app/adapters/_appium_search.py`
`search_store_via_appium(driver, store_id, locators, query)` — the
generic engine. Loops once per requested product (quick-commerce apps
search one term at a time), types the query, waits for result cards,
then extracts each card's fields via *relative* lookups
(`card.find_element(...)`, scoped to that specific card element, not the
whole screen). A card missing a required sub-element is skipped and
logged rather than aborting the entire search — one bad card shouldn't
lose every other valid result on the same screen.

### `app/adapters/{store}/appium_adapter.py`
Each ~90-line class: `_ensure_session()` starts an Appium session
(idempotent — a no-op if already active) using
`build_android_capabilities()` (Phase 6) plus the store's `app_package`/
`app_activity`. `search()` delegates to the engine, and on any failure
captures a screenshot before re-raising as `AutomationError` — giving you
a visual of exactly what the app screen looked like when the placeholder
locators (inevitably, today) failed to find anything.
`add_to_cart`/`checkout` raise `NotImplementedError` with a message
pointing at the Phase 7 mock if you need one of those right now.

---

## 6. Manual Testing & Verification

### Unit tests (no device/emulator needed)

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/adapters/ -v
```

**Expected:** 58 tests pass in `tests/adapters/` (Phase 7's existing 29 +
this phase's 29 new: 3 + 5 + 21).

### What you must do before any of this can search a real app

1. **Install the real store app** (Zepto/Blinkit/Instamart) on your
   device or emulator.
2. **Run Appium Inspector** (bundled with Appium Desktop, or the
   standalone `appium-inspector` package) against a live session pointed
   at the app.
3. **Navigate to the search screen**, inspect the search box element —
   note its real `resource-id` (or `accessibility id`, or a working
   XPath).
4. **Perform a real search**, inspect one result card and its title/
   price/ETA/quantity sub-elements.
5. **Edit `app/adapters/{store}/locators.py`**, replacing every
   `"CHANGE_ME_..."` value with what you actually observed. Remove the
   `test_all_placeholder_values_are_unmistakably_marked` assertions for
   that store from `tests/adapters/test_locators.py` once done — that
   test is an intentional tripwire meant to fail until real values exist.
6. **Verify app_package/app_activity** — `adb shell dumpsys window | grep -E 'mCurrentFocus'` while the real app is in the foreground will show both.

### Smoke-test script (after step 5 is done for at least one store)

```python
from app.core.dependencies import create_zepto_appium_adapter
from app.adapters.types import SearchQuery
from app.domain.product import ProductRequest

adapter = create_zepto_appium_adapter()
query = SearchQuery(products=[ProductRequest(name="onion")])
results = adapter.search(query)
for r in results:
    print(r.raw_title, r.raw_price, r.raw_eta, r.raw_quantity)
```

**Expected (only after real locators are supplied):** real product
listings printed. **Before that:** an `AutomationError` — this is the
correct, documented behavior, not something to debug as if it were a
bug in the automation engine itself.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `AutomationError: Search failed for store 'zepto'...` with placeholder locators still in place | Expected — see §0 | Complete the Appium Inspector steps in §6 before expecting real results. |
| `AutomationError` even AFTER supplying real locators | Locator is technically valid but doesn't match what's currently on screen (app UI changed, or navigation assumption wrong — e.g. a location-picker popup appeared first) | Check the screenshot path in the error message; compare against Appium Inspector's live view. |
| `search()` seems to hang for a long time before failing | Default `timeout=10.0` per product — normal for a genuinely slow app, or a sign every locator is wrong and you're waiting out the full timeout each time | Pass a shorter `timeout=` while iterating on locators, restore the default once they're confirmed working. |
| Results come back but fields are empty/garbled | Wrong *relative* locator for a sub-element (e.g. `title` locator actually matches a container, not the text element) | Re-inspect that specific sub-element in Appium Inspector — the parent `product_card` locator being right doesn't guarantee the child locators are. |

---

## 8. Edge Cases Considered

- **Zero result cards for a search term** — `wait_for_element` on
  `product_card.product_card` times out, which propagates as
  `AutomationTimeoutError` → caught by the adapter's `search()` → wrapped
  as `AutomationError` with a screenshot. Not currently distinguished
  from "the locator is simply wrong" — both look identical from this
  layer's perspective, which is an honest limitation (see §11).
- **All cards on a screen malformed** — returns an empty list for that
  product rather than crashing (tested explicitly).
- **`_ensure_session()` called when already active** — no-op, verified
  via a call-counting fake factory.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/adapters/ -v` — 58/58 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (proof nothing in `graph/` changed).
- [ ] (Once real locators supplied for at least one store) the smoke test in §6 returns real product data.

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] `_appium_search.py` fully runtime-verified in this sandbox against
      a behaviorally faithful `selenium` stub: single-product field
      extraction, multi-product loop + aggregation, malformed-card
      skipping, optional-locator "unknown" fallback.
- [x] `ZeptoAppiumAdapter` fully runtime-verified end-to-end: session
      lifecycle (`get_store_id`, `is_available`, `_ensure_session`
      capability-building and idempotency), and — critically — the exact
      real-world outcome expected TODAY with placeholder locators: a
      failing search correctly raises `AutomationError` and captures a
      screenshot. `add_to_cart`/`checkout` confirmed to raise
      `NotImplementedError`.
- [x] Locator placeholder values confirmed unmistakably marked (`CHANGE_ME` prefix) across all three stores.
- [x] `app/graph/` untouched — Phase 5's 40 tests remain exactly as they were.

---

## 11. Known Limitations

- **All three stores' locators are placeholders.** This is the phase's
  central, unavoidable limitation — not fixable without real device
  access, stated as plainly as possible throughout this document.
- **No handling of real per-app navigation quirks** — login prompts,
  location-picker popups, permission dialogs. The generic search engine
  assumes "type query → results appear," which may not hold for any
  given real app's first-launch flow.
- **"Zero results" and "locator is wrong" look identical** from this
  layer — both surface as a timeout. A future improvement could
  distinguish them (e.g. checking for an app-specific "no results found"
  element before concluding failure).
- **No retry-with-backoff at this layer** — Phase 5's graph-level
  `retry_orchestration` node exists for this, but isn't wired to call
  these real adapters yet (§0 of this doc and Phase 7's doc both explain
  why integration waits for Phase 15).

## 12. Improvements to Consider Later

- Once real locators exist for at least one store, consider adding a
  dedicated "no results found" detection to distinguish genuine
  zero-result searches from broken locators.
- Add per-app navigation setup hooks (e.g. a `dismiss_popups()` step) if
  real apps turn out to need them — the generic engine deliberately
  doesn't guess at this now.
- Once Phase 14 exists, revisit whether `add_to_cart`'s parameter type
  should change from `RawProductResult` to whatever Phase 10/11 end up
  defining.

---

## Next Step

Once `pytest tests/adapters/ -v` passes locally (58/58) and — ideally —
you've completed the Appium Inspector steps for at least one store and
confirmed the smoke test in §6 returns real data, say **"Move to Phase 9"**
to build the Verification Layer: parsing these raw string fields into
real, validated numbers, and rejecting malformed/duplicate results.
