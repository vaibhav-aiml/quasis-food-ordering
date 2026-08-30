# Phase 14 — Order Executor

> **Status:** Real add-to-cart and checkout automation. The safety rule
> repeated twice in the master prompt — never automatically confirm
> payment — is enforced **structurally**, not just by convention.

---

## 1. Goal

Implement the cart/checkout methods Phase 8 deliberately left as
`NotImplementedError`: add a specific product to cart, navigate through
checkout, and verify the payment screen was reached — without ever
tapping anything that would confirm or place the order.

---

## 2. Concepts to Learn From This Phase

- **A safety rule enforced by what a type *can* represent, not just what
  code chooses to do.** `CheckoutLocators` has exactly three fields.
  There is no field for a "Pay Now" button — so the automation has no
  data path to reference one, even hypothetically. This is the same
  structural-enforcement idea as Phase 11's "never use an LLM" AST test,
  applied to a physical-consequence safety rule instead of an
  architectural one.
- **Proving a negative by tracking behavior, not just checking output.**
  The core test doesn't just assert the checkout function *returns*
  something reasonable — it asserts a specific element's `.click()` was
  *never called*, while confirming the *other* two elements' clicks
  *were* called. That's what actually demonstrates selective, correct
  behavior rather than a function that happens to return the right shape.
- **Backward-compatible schema extension.** Adding `checkout` and
  `add_to_cart_button` as `Optional` fields (not required) meant Phase
  8's existing test fixtures kept working unchanged — a real example of
  "never break previous-phase functionality" when new code genuinely
  needs to extend an old contract.
- **Different error-handling philosophies for different risk profiles.**
  `search()` (Phase 8) raises on failure. `add_to_cart`/`checkout`
  (this phase) return typed failure results instead. Both are
  deliberate, and the difference is explained, not accidental.

---

## 3. Architecture Fit

Extends `app/adapters/locators.py` (backward compatibly), adds
`app/adapters/_appium_order.py` (the engine, mirroring `_appium_search.py`'s
placement and style), and updates the three `*AppiumAdapter` classes to
implement `add_to_cart`/`checkout` for real — completing the
`StoreAdapter` protocol from Phase 7 with genuine (if placeholder-locator-
blocked) automation. Not wired into `graph/`, consistent with Phases
7–13.

---

## 4. Folder Structure (this phase's changes in bold)

```
backend/app/adapters/
├── locators.py                     *(edited: + CheckoutLocators, + optional new fields)*
├── _appium_order.py               **new — the order-execution engine**
├── zepto/
│   ├── locators.py                   *(edited: + checkout/add_to_cart_button placeholders)*
│   └── appium_adapter.py               *(edited: real add_to_cart/checkout)*
├── blinkit/  (same edits)
└── instamart/  (same edits)

backend/tests/adapters/
├── test_locators.py                 *(edited: + 3 new tests)*
├── test_appium_order.py           **new**
└── test_appium_adapters.py          *(edited: NotImplementedError tests replaced)*
```

---

## 5. File-by-File Explanation

### `app/adapters/locators.py`
`CheckoutLocators` — exactly `cart_icon`, `proceed_to_checkout_button`,
`payment_screen_indicator`. No fourth field exists for anything
payment-execution-related — this is the structural guarantee described
in §2, enforced by `test_checkout_locators_has_no_payment_confirmation_field`.
`ProductCardLocators` gains an optional `add_to_cart_button`;
`StoreLocatorConfig` gains an optional `checkout` — both `Optional` so
Phase 8's fixtures keep working without modification.

### `app/adapters/_appium_order.py`
`add_product_to_cart_via_appium()` — re-searches for the product by
exact title (the `RawProductResult` handed in doesn't carry a live
element reference), finds the matching card, taps its add-to-cart
button. Every failure path returns a typed `CartActionResult(success=False, ...)`,
never raises.

`checkout_via_appium()` — taps `cart_icon`, taps
`proceed_to_checkout_button`, then calls `wait_for_element` (a
**presence check only**) on `payment_screen_indicator`. That's the
entire implementation of "verification before final order." Nothing
after that wait call exists in this function — there's no further step
to accidentally add a payment tap to.

### `app/adapters/{store}/locators.py`
Extended with the same `CHANGE_ME_...` placeholder discipline as Phase
8 — new fields for the add-to-cart button and the three checkout
locators, all obviously fake, all requiring real Appium Inspector
values before they'll work.

### `app/adapters/{store}/appium_adapter.py`
`add_to_cart`/`checkout` now call the engine functions instead of
raising `NotImplementedError`. Both start the session first via the
existing `_ensure_session()` from Phase 8.

---

## 6. Manual Testing & Verification

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/adapters/ -v
```

**Expected:** 68 tests pass in `tests/adapters/` (up from Phase 8's 58 —
this phase adds `test_appium_order.py`'s 7, updates 3 tests in
`test_locators.py`, and replaces 2 outdated tests in
`test_appium_adapters.py` with new ones covering the same count).

### The one test worth reading yourself

`test_checkout_taps_cart_and_proceed_but_never_taps_payment_indicator` in
`tests/adapters/test_appium_order.py` — this is the test that actually
matters for this phase's safety guarantee. It tracks `.click()` calls on
three fake elements and asserts two were tapped while the third
(`payment_screen_indicator`) explicitly was not.

### Real-device note

Same situation as Phase 8: today's `CHANGE_ME` placeholder locators mean
`add_to_cart`/`checkout` will return typed failures against any real
app until you complete the Appium Inspector steps from Phase 8 §6 —
now also inspecting the cart screen, the checkout screen, and an
element that only appears on the payment screen.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `add_to_cart` always returns `success=False` | Expected with placeholder locators | Same situation as Phase 8's search — supply real locators first. |
| `checkout` returns `status="failed"` with `"No checkout locators configured"` | `StoreLocatorConfig.checkout` is `None` for that store | Confirm the store's `locators.py` sets `checkout=CheckoutLocators(...)`, not `None`. |
| Worried the automation might tap a real payment button | It structurally cannot — see §2 | `CheckoutLocators` has no field to hold such a locator. Re-read `test_checkout_locators_has_no_payment_confirmation_field` for the enforcement. |

---

## 8. Edge Cases Considered

- **Product re-search finds multiple similarly-named cards** — exact
  (case-insensitive) title match required; the first exact match wins,
  others ignored.
- **`checkout` called with `locators.checkout is None`** — clean typed
  failure, not an `AttributeError` from trying to access a missing field.
- **Any exception during cart/checkout navigation** — caught, a
  screenshot attempted, and a typed failure returned; the caller never
  needs a try/except around these calls.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/adapters/ -v` — 68/68 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).
- [ ] `test_checkout_locators_has_no_payment_confirmation_field` passes — the structural safety guarantee holds.

---

## 10. Verification Checklist

- [x] All new/changed files pass `py_compile`.
- [x] Structural safety check runtime-verified: `CheckoutLocators` has
      exactly 3 fields, none resembling a payment-execution control.
- [x] Backward compatibility runtime-verified: Phase 8-style
      `StoreLocatorConfig` fixtures (no `checkout`, no
      `add_to_cart_button`) still construct without error.
- [x] **The core safety behavior runtime-verified against a behaviorally
      faithful selenium stub**: `checkout_via_appium` taps `cart_icon`
      and `proceed_to_checkout_button`, but never calls `.click()` on
      `payment_screen_indicator` — confirmed by tracking click calls on
      all three elements, not just checking the return value.
- [x] `add_product_to_cart_via_appium` verified: exact-title re-search
      and tap, product-not-found handling, missing-locator handling.
- [x] Real per-store locator files verified to have the new fields
      populated with correctly-marked `CHANGE_ME` placeholders.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- Locators are still placeholders (inherited from Phase 8) — this
  phase's engine is correct and tested; it cannot succeed against a
  real app until real values are supplied.
- Re-searching by exact title to find a live element for add-to-cart
  duplicates a little of Phase 8's search logic rather than reusing
  `search_store_via_appium` directly — a documented, justified tradeoff
  (that function returns parsed data, not live element handles).
- No quantity selection before add-to-cart (e.g. "add 2, not 1") — out
  of scope for this phase's minimal flow; would need a real app's
  quantity-stepper UI inspected first.
- No explicit "already in cart" detection — re-adding a product that's
  already in the cart is assumed to behave however the target app
  naturally handles that (increment quantity, no-op, etc.), untested
  since it depends entirely on real app behavior.

## 12. Improvements to Consider Later

- Once real locators exist, consider whether `add_to_cart` can skip the
  re-search step if the original search results are still on screen
  (an optimization, not a correctness fix).
- Add quantity-selection support if a real app's flow requires it.
- Consider a `cart_contents_indicator` locator (verify the cart actually
  contains what was added) as an additional check before proceeding to
  checkout, if real usage shows silent add-to-cart failures are common.

---

## Next Step

Once `pytest tests/adapters/ -v` passes locally (68/68), say
**"Move to Phase 15"** to begin Integration Testing — connecting every
standalone layer built since Phase 7 (adapters, verification,
normalization, ranking, recommendation, approval, order execution) into
the actual LangGraph workflow, with sequence diagrams, failure scenarios,
and recovery strategies.
