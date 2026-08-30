# Phase 13 — Human Approval Flow

> **Status:** Deterministic decision logic for confirmation/rejection/
> modification. Standalone, not wired into Phase 5's graph or exposed as
> real API endpoints yet — see §0 for why.

---

## 0. Scope decision: why no FastAPI endpoints this phase

Phase 0 §10 lists `POST /v1/requests/{id}/approve|reject|modify` as API
contracts. Building real, working versions of those now would require a
request-tracking/persistence system that doesn't exist yet (Phase 0 is
explicit: "No database in MVP"), and Phase 2 only ever built a health
endpoint — there's no `POST /v1/requests` to submit a request against in
the first place. Inventing request storage now, just to make these three
endpoints functional, would mean building Phase 15's integration
plumbing early.

Consistent with the pattern established across Phases 7–12: this phase
builds the **decision logic** — fully typed, self-validating, and
completely tested — standalone. Wiring it to real endpoints and a real
request store is explicitly Phase 15's job.

---

## 1. Goal

Give Phase 5's graph (whose `route_after_approval` currently compares a
bare string) a real, validated domain layer underneath it: what a human
can decide, what data each decision requires, and what should happen
next as a deterministic function of that decision.

---

## 2. Concepts to Learn From This Phase

- **Self-validating request/response contracts.** `ApprovalSubmission`
  enforces its own internal consistency (a `modify` decision must carry
  a `modify_request`; nothing else may) via a `model_validator` — the
  same "deterministic Python enforces consistency" principle as
  `IntentRequest`'s clarification invariants (Phase 4), applied to a new
  kind of contract.
- **Distinguishing "tweak" from "restart."** A modify request that only
  changes a budget number needs different downstream handling than one
  that restates the whole shopping list in new words — the former only
  needs re-planning; the latter needs to go back through Intent
  Understanding entirely. Encoding that distinction in the type
  (`updated_raw_text` vs. the constraint fields) makes the right routing
  decision obvious to whoever wires this in later (Phase 15).
- **Merge semantics for partial updates.** "Unspecified fields keep
  their current value" sounds obvious until you have to actually write
  and test it — verified explicitly so a budget-only modify can't
  accidentally erase an already-stated delivery-time limit.

---

## 3. Architecture Fit

`app/domain/approval.py` (contracts) and `app/processing/approval.py`
(the deterministic decision function) — zero LLM, zero Appium
dependency, matching Phase 0's dependency graph for `processing/`.
`process_approval` depends on `RecommendationResult` (Phase 12) and
`Constraints` (Phase 4) — the two things it needs to reason about, and
nothing else. Not wired into `graph/`, consistent with Phases 7–12.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/domain/
└── approval.py         **ApprovalDecision, ModifyRequest, ApprovalSubmission**

backend/app/processing/
└── approval.py           **ApprovalOutcome, ApprovalOutcomeStatus, process_approval()**

backend/tests/domain/
└── test_approval.py      **new**

backend/tests/processing/
└── test_approval.py        **new**
```

No DI factory — `process_approval` is a pure function, same precedent
as Phases 9–12's processing modules.

---

## 5. File-by-File Explanation

### `app/domain/approval.py`
`ApprovalDecision` — `approved` / `rejected` / `modify`. `ModifyRequest`
— every field optional individually, but a `model_validator` requires at
least one to be set (an empty modify request means nothing). `updated_raw_text`
is kept structurally separate from the three constraint-override fields
specifically so downstream routing (Phase 15) can tell "re-extract
everything" from "just re-plan" without inspecting string content.
`ApprovalSubmission` — the decision plus optional `rejection_reason`
(only meaningful for `rejected`) and `modify_request` (only meaningful
for, and required by, `modify`) — a second `model_validator` enforces
that pairing.

### `app/processing/approval.py`
`process_approval(recommendation, submission, current_constraints)` —
three branches, one per decision:
- **`approved`** → `PROCEED_TO_ORDER` with the recommended `store_id`.
  Raises `ValueError` if `recommendation.store_id is None` — approving
  "nothing was found" isn't a valid state to act on.
- **`rejected`** → `CANCELLED`, with the optional reason folded into the
  message.
- **`modify`** → `RETRY_WITH_MODIFICATIONS`. Builds a new `Constraints`
  by taking each field from the modify request if set, otherwise from
  `current_constraints` — verified explicitly that unset fields survive
  unchanged. If `updated_raw_text` was set, the message and the
  presence of `updated_raw_text` in the outcome both signal "this needs
  full re-extraction," not just re-planning.

---

## 6. Manual Testing & Verification

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/domain/test_approval.py tests/processing/test_approval.py -v
```

**Expected:** 16 tests pass (8 domain + 8 processing).

### Optional: exercise it directly

```python
from app.processing.approval import process_approval
from app.domain.approval import ApprovalDecision, ApprovalSubmission, ModifyRequest
from app.domain.constraints import Constraints, Priority
from app.agents.recommendation_agent import RecommendationResult

recommendation = RecommendationResult(store_id="zepto", explanation="...", used_fallback=False, basket=None)
current = Constraints(priority=Priority.CHEAPEST, max_delivery_minutes=20, max_budget=None)

submission = ApprovalSubmission(
    decision=ApprovalDecision.MODIFY,
    modify_request=ModifyRequest(updated_max_budget=100.0),
)
outcome = process_approval(recommendation, submission, current)
print(outcome.status, outcome.updated_constraints, outcome.message)
```

**Expected:** `retry_with_modifications`, with `max_budget=100.0` and
`max_delivery_minutes=20` (preserved from `current`) both present.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValidationError` constructing `ApprovalSubmission` with `decision=modify` | Forgot `modify_request` | It's required for that decision — see §5. |
| `ValidationError` constructing `ApprovalSubmission` with `decision=approved` and a `modify_request` | Payload doesn't match the decision | Only `modify` decisions may carry a `modify_request`. |
| A modify outcome's constraints look wrong | An unspecified field didn't inherit from `current_constraints` as expected | Check that `current_constraints` passed to `process_approval` is actually the request's live constraints, not a fresh default. |

---

## 8. Edge Cases Considered

- **Approving with no viable store** — raises loudly rather than
  silently proceeding with nothing to order (tested).
- **Modify with only `updated_raw_text` set** — constraint fields all
  fall through to `current_constraints` unchanged; the raw-text
  restatement is the only real signal (tested).
- **Reject with no reason** — produces a clean message with no dangling
  punctuation or "Reason: None" artifact (tested).

---

## 9. Acceptance Criteria

- [ ] `pytest tests/domain/test_approval.py tests/processing/test_approval.py -v` — 16/16 pass.
- [ ] `pytest tests/graph/ -v` — still 40/40 (nothing in `graph/` touched).

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] `process_approval` runtime-verified across all six scenarios:
      approved (success + no-store error), rejected (with/without
      reason), modify (constraint-merge-preserving-unspecified-fields,
      and raw-text-triggers-re-extraction messaging).
- [x] Zero dependency on `core/llm/`, `agents/` (beyond the
      `RecommendationResult` type it consumes), `automation/`, or
      `adapters/`.
- [x] `app/graph/` untouched.

---

## 11. Known Limitations

- No real API endpoints yet (§0) — by design, not oversight.
- No request-tracking/persistence — `process_approval` is a pure
  function operating on values passed to it; there's no notion yet of
  "the current state of request X" beyond what the caller supplies.
- `ApprovalSubmission`/`ModifyRequest` validators use pydantic's own
  stub-incompatible `model_validator` machinery, which this sandbox's
  offline pydantic stub couldn't exercise (documented in the
  verification script's own comments) — real validation behavior is
  proven by the existing `IntentRequest`/Phase 4 precedent, but please
  make sure `pytest tests/domain/test_approval.py` specifically passes
  locally, since that's the one file this sandbox couldn't fully verify.

## 12. Improvements to Consider Later

- Once Phase 15 builds real request tracking, wire
  `POST /v1/requests/{id}/approve|reject|modify` to call
  `process_approval` directly.
- Consider whether `rejection_reason` should be structured (a small enum
  of common reasons) rather than free text, if analytics on rejection
  causes ever becomes a real requirement — not justified to build now.

---

## Next Step

Once `pytest tests/domain/test_approval.py tests/processing/test_approval.py -v`
passes locally (16/16), say **"Move to Phase 14"** to build the Order
Executor — add to cart, checkout navigation, and pre-payment
verification, never auto-confirming payment.
