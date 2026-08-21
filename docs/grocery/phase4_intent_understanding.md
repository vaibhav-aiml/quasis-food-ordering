# Phase 4 — Intent Understanding

> **Status:** First domain-specific agent. Converts free text into a
> validated `IntentRequest`. Still no LangGraph (Phase 5), no Appium, no
> real store data — this agent's whole job ends the moment it returns a
> structured object.

---

## 1. Goal

Prove the LLM layer built in Phase 3 can reliably do real work: take a
sentence like *"I'm making biryani, need onions and curd, cheapest option
under 20 minutes"* and produce a validated `IntentRequest` — the exact
contract every later phase (planning, ranking, ordering) will consume.

---

## 2. Concepts to Learn From This Phase

- **Splitting "what the LLM outputs" from "what the domain model looks
  like"** — `_ExtractedIntent` vs. `IntentRequest`, and why `raw_text` is
  deliberately excluded from the LLM's job.
- **Pydantic validators as the home for deterministic normalization** —
  why `ProductRequest.name` trimming/lowercasing lives in the model, not
  in agent code.
- **Testing an agent without a real LLM** — composing a fake client with
  the *real* `StructuredLLMService`, so the test exercises real
  render/parse/validate logic while controlling exactly what "the model"
  says.
- **Confidence as a first-class field**, not an afterthought — the LLM
  self-reports how sure it is, which later phases (not this one) can use
  to decide whether to ask the user for clarification.

---

## 3. Architecture Fit

Implements the `agents/` box from Phase 0 §2/§5.1 — reasoning only. Nothing
in `intent_agent.py` makes a ranking or ordering decision; it produces data,
full stop. Depends on `domain/` (the contracts) and `core/llm/`
(`StructuredLLMService`) — exactly the dependency graph from Phase 0 §9.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/domain/
├── constraints.py       **Priority enum + Constraints**
├── product.py             **ProductRequest**
└── intent.py                **IntentRequest**

backend/app/agents/
└── intent_agent.py          **IntentUnderstandingAgent + merge_duplicate_products()**

backend/app/core/llm/prompt_templates/
└── intent_extraction.txt    **new**

backend/tests/domain/
├── test_product.py           **new**
├── test_constraints.py        **new**
└── test_intent.py               **new**

backend/tests/agents/
└── test_intent_agent.py         **new**
```

`app/core/dependencies.py` gets `get_intent_agent()`.

---

## 5. File-by-File Explanation

### `app/domain/constraints.py`
`Priority` is a `str, Enum` (`cheapest` / `fastest` / `best_value`) — string
subclassing means it serializes as a plain string automatically, no custom
JSON encoder needed anywhere it's used. `Constraints.priority` defaults to
`BEST_VALUE`, enforced as a Pydantic field default rather than something
the LLM is trusted to always fill in sensibly.

### `app/domain/product.py`
`ProductRequest.name` and `.unit` are normalized (trim + lowercase) via
`@field_validator`, so this invariant holds for *every* construction path
— LLM extraction today, direct API input in a later phase, anything. A
blank name/unit (even one that's blank only after trimming, e.g. `"   "`)
is rejected at construction time, not silently accepted.

### `app/domain/intent.py`
`IntentRequest` requires at least one product (`min_length=1`) — an intent
with zero products isn't a valid shopping request and shouldn't be
representable at all. `confidence` is bounded `[0.0, 1.0]` by the type
itself.

### `app/core/llm/prompt_templates/intent_extraction.txt`
Explicit instructions on: product name casing, when to omit
quantity/unit (letting Python defaults apply), how to map user wording to
`priority`, and — critically — a direct instruction not to include the
user's raw text in the response at all.

### `app/agents/intent_agent.py`
Two things live here:

**`_ExtractedIntent`** — the LLM's actual output contract: `products`,
`constraints`, `confidence`. No `raw_text` field exists on this class at
all, so there's no way for the agent to accidentally trust an LLM-produced
version of the user's own words.

**`merge_duplicate_products()`** — pure, standalone function. If the LLM
extracts "onion" twice (e.g. once from "onions" and once from a later
clause), this merges them by summing quantities — but *only* when the unit
also matches; "2 onion" and "1 kg onion" are kept separate rather than
silently summed into a meaningless "3". This asymmetry (merge same-unit,
never merge cross-unit) is the one subtle design decision in this file,
and it's exactly the kind of thing that's cheap to get right in
deterministic Python and expensive to get right by hoping the LLM
remembers not to double-count.

**`IntentUnderstandingAgent.extract()`** — the orchestration: validates
`raw_text` isn't empty, calls `StructuredLLMService.generate()` for the
`_ExtractedIntent`, then constructs the real `IntentRequest` with
`raw_text` set from the original Python string and products passed through
`merge_duplicate_products()`.

---

## 6. Example Prompts and Expected Outputs

These are the request/response pairs the prompt template and domain
models are designed against. Useful as a manual sanity check once you run
this against a real model in §7.

### Example 1 — the canonical case

**Input:**
> "I am making biryani. I need onions and curd. Find the cheapest option that can deliver within 20 minutes."

**Expected `IntentRequest` (shape):**
```json
{
  "raw_text": "I am making biryani. I need onions and curd. Find the cheapest option that can deliver within 20 minutes.",
  "products": [
    {"name": "onion", "quantity": 1.0, "unit": "unit"},
    {"name": "curd", "quantity": 1.0, "unit": "unit"}
  ],
  "constraints": {
    "max_delivery_minutes": 20,
    "priority": "cheapest",
    "max_budget": null
  },
  "confidence": 0.9
}
```
Note `raw_text` is exactly the input string, byte for byte — Python's
doing, not the LLM's.

### Example 2 — explicit quantities and urgency wording

**Input:**
> "Order 2kg onions and 500ml milk, need it ASAP."

**Expected shape:**
```json
{
  "products": [
    {"name": "onion", "quantity": 2.0, "unit": "kg"},
    {"name": "milk", "quantity": 500.0, "unit": "ml"}
  ],
  "constraints": {
    "max_delivery_minutes": null,
    "priority": "fastest",
    "max_budget": null
  }
}
```
"ASAP" maps to `priority: fastest` per the prompt's explicit wording
instructions; no delivery-minute number was given, so it stays `null`.

### Example 3 — budget constraint, no time pressure

**Input:**
> "I want to buy bread and eggs, budget is under 200 rupees."

**Expected shape:**
```json
{
  "products": [
    {"name": "bread", "quantity": 1.0, "unit": "unit"},
    {"name": "eggs", "quantity": 1.0, "unit": "unit"}
  ],
  "constraints": {
    "max_delivery_minutes": null,
    "priority": "best_value",
    "max_budget": 200.0
  }
}
```
No urgency or cheapness wording, so `priority` falls back to
`best_value`, and `max_budget` is captured.

### Example 4 — vague request (low-confidence case)

**Input:**
> "get me something for dinner"

**Expected behavior:** the LLM should produce a *low* `confidence` value
(e.g. `0.2–0.4`) and either a best-guess product list or, in the worst
case, fail schema validation entirely (since `products` requires
`min_length=1` — a genuinely empty extraction would trigger the
`StructuredLLMService` retry loop, and if that's exhausted, raise
`LLMValidationError`). This example exists specifically to document that
low-confidence handling (asking the user to clarify) is **not** this
phase's job — it's a routing decision for the LangGraph `Failed`/retry
logic in Phase 5.

---

## 7. Manual Testing & Verification

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt   # if not already done

pytest tests/domain/ tests/agents/test_intent_agent.py -v
```

**Expected:** 22 tests pass (6 in `test_product.py` + 6 in
`test_constraints.py` + 5 in `test_intent.py` + 9 in
`test_intent_agent.py`).

### Optional: run against a real Ollama model

```python
# From backend/, with venv active: python3
from app.core.dependencies import get_intent_agent

agent = get_intent_agent()
result = agent.extract(
    "I am making biryani. I need onions and curd. "
    "Find the cheapest option that can deliver within 20 minutes."
)
print(result.model_dump_json(indent=2))
```

**Expected:** output matching the shape of Example 1 above (exact
`confidence` value will vary — that's expected, it's the model's own
self-assessment).

---

## 8. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValidationError: products / Field required` from the LLM's raw output | Model produced an empty or malformed `products` array | Check `LLMValidationError.raw_response` (raised after retries exhausted) to see what the model actually said; may need prompt tuning. |
| Product quantities look wrong after extraction | Duplicate products with *different* stated units weren't merged (by design) | Confirm this is actually the cross-unit case — if so, that's correct behavior, not a bug (see §5). |
| `confidence` always comes back suspiciously high (e.g. always `0.95`) even for vague input | Model isn't genuinely calibrating confidence | Known LLM limitation, not a code bug — worth prompt-engineering if it matters for your use case; flagged in §12. |
| Product name has inconsistent casing somewhere downstream | Bypassing `ProductRequest`'s validator (e.g. mutating `.name` after construction) | Never mutate a validated model's fields directly — construct a new instance if a value needs to change. |

---

## 9. Edge Cases Considered

- **Same product, different units** → kept as separate `ProductRequest`
  entries by design (§5) — tested explicitly in
  `test_merge_keeps_separate_entries_for_different_units`.
- **Empty/whitespace-only input** → rejected before any LLM call at all
  (`extract()` raises `ValueError` immediately) — no wasted LLM round-trip
  for obviously invalid input.
- **LLM's first response is malformed** → recovered via
  `StructuredLLMService`'s existing retry mechanism (Phase 3) — Phase 4
  didn't need to reimplement retry logic, only supply the right
  `response_model`.
- **User states a budget but no delivery time, or vice versa** — both
  fields are independently optional on `Constraints`; nothing forces one
  to imply the other (Examples 2 and 3 above cover both directions).

---

## 10. Acceptance Criteria

- [ ] `pytest tests/domain/ tests/agents/test_intent_agent.py -v` — 59/59 pass.
- [ ] (Optional) live Ollama run on Example 1 produces the expected shape.
- [ ] Live Ollama run on `"get me something for dinner"` returns
      `products: []`, `needs_clarification: true`, `confidence <= 0.5` —
      not invented products. (This case now shouldn't reach Ollama at
      all — check application logs for `intent_agent_short_circuited_vague_request`.)
- [ ] `app/agents/intent_agent.py` contains zero references to Appium, adapters, or ranking — reasoning only.

---

## 11. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] `merge_duplicate_products()` runtime-verified in this sandbox (with
      a minimal `pydantic` stub, since the real package isn't installable
      offline here) — confirmed it sums same-name-same-unit, keeps
      different-unit entries separate, and preserves first-occurrence
      order.
- [ ] Full `pytest` suite (needs real `pydantic`/`pydantic-settings`) — run locally to confirm all 22 pass.
- [x] `domain/` models have zero dependency on `agents/`, `core/llm/`, or anything else in `app/` — only on `pydantic` itself.
- [x] `raw_text` is never part of the LLM's output schema (`_ExtractedIntent` has no such field) — verified by inspection.

---

## 12. Known Limitations

- LLM-reported `confidence` isn't independently validated against
  anything — it's exactly as reliable as the model's self-assessment,
  which is a known soft spot for LLMs in general. No downstream logic
  should treat it as a precise probability, only a rough signal.
- No handling yet for genuinely unsupported products (e.g. someone asks
  for something no supported store would carry) — that surfaces naturally
  later (Planning Agent / Verification Layer), not here.
- `merge_duplicate_products()` uses exact string equality on
  already-normalized names — "onion" and "onions" (if the LLM
  inconsistently singularizes) would NOT be merged. The prompt explicitly
  asks for singular form to minimize this, but it's not enforced in code.

## 13. Improvements to Consider Later

- If confidence calibration proves unreliable in practice, consider a
  cheaper deterministic sanity check (e.g. flag suspiciously generic
  product names) rather than trusting the LLM number alone.
- Consider a small synonym-normalization step (e.g. "onions" → "onion")
  if inconsistent singularization from the LLM turns out to be common —
  would live in `ProductRequest`'s validator, staying consistent with
  "normalization lives in the domain model" from this phase's design.

---

## 14. Bugfix Log

### Bug: `max_delivery_minutes` extracted as `null` despite explicit "deliver within 20 minutes"

**Discovered:** live run against a real Ollama model on the canonical
Example 1 request.

**Root cause:** `_ExtractedIntent.constraints` originally reused the
domain `Constraints` model directly as the LLM's output target.
`Constraints.max_delivery_minutes: int | None = Field(default=None, ge=1)`
renders in JSON Schema as `"anyOf": [{"type": "integer", "minimum": 1},
{"type": "null"}]`, and — because it carries a Python-level default — is
**omitted from the schema's `"required"` list**. A field that is both
nullable and non-required is a documented failure mode for
schema-constrained LLM decoding (including Ollama): it's exactly the
shape a constrained decoder is most likely to default to `null` on, even
when the source text clearly states a value. `max_budget` had the
identical defect, latent but unobserved.

**Fix (scoped to this phase's agent + prompt only):**
- Added `_ExtractedConstraints` — a private, LLM-facing schema in
  `app/agents/intent_agent.py` with every field **required** and
  **non-nullable**, using `0` as an explicit "not stated" sentinel for
  both numeric fields (safe, since the domain model rejects `0` as a real
  value on both fields anyway).
- Added `_to_domain_constraints()` — a small, pure Python function mapping
  the sentinel-based extraction to the domain `Constraints`'s real
  `Optional` semantics (`0 or None`).
- Reworded `intent_extraction.txt`'s constraints section to instruct the
  model to always include all three fields, using `0` for anything unstated.
- **Explicitly not changed:** `app/domain/constraints.py` (the domain
  `Constraints` type is correct as-is — this was never a domain-modeling
  bug, only a mismatch between the domain model's natural shape and what
  a constrained decoder handles reliably), `StructuredLLMService`,
  `PromptManager`, `LLMClient`, and anything Phase 5+.

**Regression tests added** (`tests/agents/test_intent_agent.py`):
- `test_extract_recovers_max_delivery_minutes_from_canonical_biryani_request`
  — the specific case that broke, using the exact canonical request wording.
- `test_extracted_constraints_schema_has_no_nullable_delivery_minutes_field`
  — asserts the schema shape itself (required + non-nullable), guarding
  against ever reintroducing the anyOf/non-required pattern regardless of
  what the prompt text says.
- `test_to_domain_constraints_maps_sentinel_zero_to_none` /
  `test_to_domain_constraints_preserves_nonzero_values` — direct unit
  tests of the new mapping function in isolation.

**Verified in this sandbox:** the sentinel-mapping logic
(`_to_domain_constraints`) was runtime-executed here against both the
`20`-minutes case and the all-zero case, using the same offline
pydantic-stub technique as earlier phases, and produced the correct
output in both cases. The full suite (now 29 tests total: 6 + 6 + 5 + 12)
still requires real `pydantic` to execute — **not run in this sandbox**,
run it locally per §7/§10 before treating this as resolved.

---

## 15. Bugfix Log (Incident 2): LLM inventing products and constraints

**Discovered:** manual Phase 4 testing. Input `"get me something for
dinner"` returned invented products (`chicken`, `rice`, `vegetables`) and
invented constraints (`max_delivery_minutes: 60`, `max_budget: 500.0`) —
none of which the user stated. This is categorically different from
Incident 1: the model wasn't leaving a field `null` under-confidently, it
was confidently fabricating data that passed schema validation perfectly.
A schema/required-field fix alone cannot catch this, since fabricated data
is well-typed data.

**Root cause:** the system had no deterministic check that extracted
products/constraints were actually grounded in the user's input — it
trusted the LLM's output (and the LLM's own `confidence`) unconditionally
as long as it validated against the schema.

**Fix — two independent layers, per the design principle that prompt
engineering alone is not a reliability guarantee:**

1. **Prompt-level** (`intent_extraction.txt`): explicit "never invent"
   instructions naming every field category, plus few-shot examples using
   your exact reported inputs ("get me something for dinner", "I need
   food", "buy something") paired with the correct empty-extraction
   response.

2. **Deterministic Python-level** (`app/agents/intent_agent.py`) — the
   layer that actually matters, since it holds regardless of LLM
   compliance:
   - `_filter_unsupported_products()` — drops any product whose name
     isn't a literal (case-insensitive) substring of the raw text.
   - `_sanitize_product_quantities()` / `_sanitize_constraints()` — zero
     out any quantity/unit/delivery-time/budget the LLM attached if the
     raw text contains **no digits at all** — a request with zero digits
     cannot legitimately contain a specific stated number.
   - `_enforce_extraction_policy()` — the final gate: forces
     `needs_clarification=True` (and caps confidence at
     `CLARIFICATION_CONFIDENCE_CEILING`, 0.5) whenever products end up
     empty, the LLM itself flagged ambiguity, or the LLM's own confidence
     was below the ceiling — regardless of what the LLM claimed about
     itself.

3. **Domain-level** (`app/domain/intent.py`) — `IntentRequest` now allows
   `products=[]`, adds `needs_clarification`/`clarification_reason`, and a
   `model_validator` makes an empty product list *illegal* unless
   `needs_clarification=True` with a real reason and capped confidence.
   This is defense in depth: even a future caller that bypasses the agent
   entirely cannot construct an inconsistent `IntentRequest`.

**Why this is a genuine fix, not a workaround:** verified in this sandbox
by directly feeding the *exact* reported hallucination (chicken/rice/
vegetables, 60-minute delivery, ₹500 budget, LLM claiming
`needs_clarification=False` at `confidence=0.8`) through
`_filter_unsupported_products`, `_sanitize_constraints`, and
`_enforce_extraction_policy`. All three hallucinated products were
rejected, both fabricated constraint numbers were zeroed, and the final
policy override forced `needs_clarification=True` with `confidence=0.5`
— overriding the LLM's own confident, incorrect self-report entirely. I
also verified the inverse: the legitimate canonical biryani request (real
product names and a real "20 minutes" digit) passes through completely
untouched, confirming the fix doesn't over-sanitize valid input.

**Compatibility with the LangGraph roadmap (Phase 5):** `needs_clarification`
is exactly the boolean a LangGraph conditional edge would branch on — this
phase intentionally stops at exposing the signal, not implementing the
routing, per the instruction to keep the fix scoped and not proceed to
Phase 5.

**Tests added** (`tests/agents/test_intent_agent.py`, now 26 tests total
in this file): isolated tests for each of the four new pure functions
(`_filter_unsupported_products`, `_sanitize_product_quantities`,
`_sanitize_constraints`, `_enforce_extraction_policy`), plus five
end-to-end scenario tests covering exactly what was requested:
`"get me something for dinner"`, `"I need food"`, `"buy something"`
(all three scripted with a *hallucinating* fake LLM to prove the
Python-side policy — not just prompt wording — is what neutralizes it),
one fully explicit valid request, and one request with explicit
constraints. `tests/domain/test_intent.py` (now 9 tests) covers the new
`model_validator` invariants directly.

**Full suite now: 47 tests** (6 + 6 + 9 + 26). Requires real `pydantic` to
execute — not run in this sandbox. Run locally per §7/§10 before treating
this as resolved.

---

## 16. Refinement: pre-LLM short-circuit for zero-information requests

**Prompted by:** a follow-up observation that Incident 2's fix, while
correct, still *calls the LLM* for "get me something for dinner" before
discarding its invented output. Since the LLM has no memory of the user's
preferences or past orders, asking it anything about "something for
dinner" is asking it to guess by construction — the request should never
reach the model at all. Recognizing "this request has zero extractable
information" is a job for the system (deterministic Python), not a
question to hand to the LLM.

**Change:** added `_looks_obviously_vague()` — a pre-LLM check in
`IntentUnderstandingAgent.extract()`. If every word in the (lowercased,
punctuation-stripped) request is in a small fixed set of generic filler
words (`get`, `me`, `something`, `food`, `buy`, `need`, `dinner`, etc.),
the method returns a clarification-needed `IntentRequest` immediately —
`products=[]`, `confidence=0.0`, `needs_clarification=True` — **without
ever calling `StructuredLLMService.generate()`**.

**Why word-set membership, not NLP/classification:** deterministic, fully
explainable, and trivially fast — consistent with "avoid overengineering."
Any word outside the fixed set (e.g. "onion", "biryani", "chicken") means
there's at least one candidate product noun, so the request still goes to
the LLM and the existing Incident 2 sanitization layers remain the
backstop for whatever comes back. This is a stronger guarantee for the
clearest cases, layered on top of (not replacing) the post-LLM defenses.

**Verified in this sandbox:** ran the word-set logic directly against 5
vague phrasings (all correctly short-circuited) and 6 concrete requests,
including the deliberately tricky `"get me onions for dinner"` — contains
"dinner" (a filler word) *and* "onions" (a real product), and correctly
did **not** short-circuit, confirming the check doesn't over-trigger on
requests that mention a vague occasion alongside a real item.

**Tests added:** `test_looks_obviously_vague_detects_filler_only_requests`
/ `..._returns_false_when_product_noun_present` (parametrized, 11 cases
total). The three required scenario tests were upgraded to prove zero LLM
calls (`FakeLLMClient` given an *empty* response list — it raises if
`.chat()` is invoked even once, so the test fails loudly if the
short-circuit ever regresses) rather than only checking the final output
shape. Added one more scenario test confirming the short-circuit and the
post-LLM sanitization layer compose correctly for a mixed case ("get me
onions for dinner" with a hallucinating fake LLM still attached).

**Full suite now: 59 tests** (6 + 6 + 9 + 38, accounting for
parametrization). Not run in this sandbox — run locally per §7/§10.

---

## Next Step

Once `pytest` passes locally (22/22) and ideally the live Ollama example
matches expectations, say **"Move to Phase 5"** to build the LangGraph
foundation — state, nodes, conditional routing, and pause/resume support,
using mocked tools (no Appium yet) to prove the graph executes end-to-end.
