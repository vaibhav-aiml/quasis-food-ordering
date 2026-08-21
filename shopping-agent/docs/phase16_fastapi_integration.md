# Phase 16 — FastAPI Integration

> **Status:** Real REST API driving the existing Phase 15 LangGraph
> workflow. No new persistence layer, no parallel architecture — the
> LangGraph checkpointer (`InMemorySaver`, keyed by `thread_id`) *is*
> the request store. Store mode remains mock/offline by default.

---

## 0. Scope

Phase 13 explicitly deferred building real `/v1/requests` endpoints
until a request-tracking system existed and there was a graph to drive
end-to-end. Phase 15 built that graph and verified it (including the
real Blinkit Appium path in the separate Phase 15(2) audit). This
phase wires FastAPI to it. Per the task brief:

- The real Blinkit Appium workflow is **untouched** except for one
  targeted graph-wiring fix (§3) required for the API's own contract
  to be trustworthy.
- Zepto/Instamart real automation: **not implemented** (still mock
  adapters by default, per `Settings.store_mode`).
- Flutter/mobile: **not started**.

---

## 1. Endpoints

All under `/v1/requests` (`app/api/v1/endpoints/requests.py`):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/requests` | Create a thread, run the graph to its first pause/terminal state. |
| `GET` | `/v1/requests/{thread_id}` | Read back the current checkpointed state. |
| `POST` | `/v1/requests/{thread_id}/selection` | Pick a specific ranked candidate before approving. |
| `POST` | `/v1/requests/{thread_id}/approval` | Resume a paused thread with an explicit `approved`/`rejected`/`modify` decision. |

The router is thin by design: intent extraction, planning, ranking,
basket selection, approval semantics, and order execution all already
live in the graph and the processing/domain layers from Phases 4-15.
This module only creates threads, reads checkpoints, validates input,
and calls `graph.invoke(...)` / `graph.update_state(...)`.

### Response shape

Every endpoint returns the same `RequestStatusResponse`: `thread_id`,
`status`, `waiting_for_approval`, `needs_clarification` (+ reason),
`intent`, `candidates` (ranked options per requested product),
`selected_indices`, `recommendation`, `ready_for_payment`,
`order_confirmation`, `error_message`.

---

## 2. Safety invariants

- **Nothing is ever auto-approved.** `POST /requests` and
  `POST /{id}/selection` never submit a decision on the caller's
  behalf — the graph run stops on its own at `awaiting_approval`'s
  `interrupt()` call. Only `POST /{id}/approval` can resume it, and
  only with a body that validates as
  `app.domain.approval.ApprovalSubmission` (reused directly as the
  request model, so "modify requires modify_request" etc. is enforced
  exactly once, in the domain layer FastAPI already validates against
  — not re-implemented in the router).
- **`ready_for_payment` is trustworthy.** The response only reports
  `ready_for_payment: true` when `checkout_state.status ==
  "ready_for_payment"` in the checkpointed state — never merely
  because the graph's terminal `status` field says so.
- **No silent multi-product selection.** `POST /{id}/selection`
  rejects (400) any product name not present in the current
  candidates, or any index outside that product's candidate list,
  rather than silently clamping or ignoring bad input.

---

## 3. Graph-side fix: `ready_for_payment` was previously unconditional

`order_execution_node` already set `status="failed"` with a reason
whenever checkout didn't reach the payment screen (bad cart items,
missing adapter, `checkout_state.status != "ready_for_payment"`). But
`build_graph()` wired `order_execution -> ready_for_payment` as an
**unconditional** edge, and `ready_for_payment_node` unconditionally
overwrote `status` to `"ready_for_payment"` — silently discarding a
real checkout failure. Under Phase 7's mock adapters (which always
succeed) this never surfaced in existing tests; it's a live risk for
the real Blinkit path, and directly violates this phase's explicit
requirement 2 ("`ready_for_payment` only when the real checkout flow
actually reached the payment screen").

Fixed with a new conditional edge (`route_after_order_execution` in
`app/graph/nodes/order_execution.py`), not by touching any Appium/
adapter code:

```python
builder.add_conditional_edges(
    "order_execution",
    route_after_order_execution,
    {"ready_for_payment": "ready_for_payment", "failed": "failed"},
)
```

Regression-tested in `tests/api/test_requests.py::
test_ready_for_payment_is_false_when_checkout_does_not_reach_payment_screen`.

---

## 4. `get_shopping_graph` is now cached

`app.core.dependencies.get_shopping_graph` previously had **no**
`@lru_cache`. Since `build_graph()` compiles with a fresh
`InMemorySaver()` every call, every dependency resolution would have
built a brand-new, empty checkpoint store — a thread created by
`POST /requests` would already be gone by the time a separate
`GET /requests/{thread_id}` call resolved its own dependency. This is
now `@lru_cache`d, making the compiled graph (and its checkpointer) a
genuine process-wide singleton, which is required for `thread_id`
based state to persist across requests at all.

A new `get_shopping_graph_dependency()` (no parameters) is what routes
actually depend on — `get_shopping_graph(settings: Settings | None =
None)`'s bare optional parameter would otherwise be mis-interpreted by
FastAPI as an incoming query parameter of type `Settings` if used
directly in `Depends(...)`.

---

## 5. Product selection semantics (preserved from Phase 15(2))

`app.processing.recommendation_selection.select_best_store(ranking_summary,
selected_indices)` already existed with this signature but was never
threaded through the graph. `GraphState` gained a `selected_indices:
dict[str, int] | None` field (default `None` — zero behavior change
when absent), and `recommendation_generation_node` now passes
`state.get("selected_indices")` through.

**Important semantic note:** an index picks among a *store's own*
ranked candidates for a product (e.g. two matching listings from the
same store) — it does not, by itself, choose which store wins the
overall recommendation. Store selection is still the existing
deterministic basket-scoring policy (fewest missing products, then
price/ETA per the resolved priority). Changing which listing a store
uses can *indirectly* shift the winning store if it changes that
store's basket total relative to others under `CHEAPEST`/`BEST_VALUE`
— this is correct, existing behavior, not a bug introduced here.

Two ways to select:

- **Up front**, in `POST /requests`'s optional `selected_indices` field
  — threaded into `GraphState` before `recommendation_generation` ever
  runs.
- **While paused**, via `POST /{thread_id}/selection` — only valid when
  the thread is genuinely waiting for approval. Recomputes
  `basket`/`recommendation` with the existing pure functions
  (`select_best_store`, `RecommendationGenerator.generate`) and writes
  them into the paused checkpoint with `graph.update_state(...)`, so
  the *next* time `awaiting_approval_node` runs (on
  `POST /{thread_id}/approval`), it re-reads state from scratch and
  uses the selection — not the original default recommendation.

### `waiting_for_approval` detection detail

`graph.update_state(...)` clears the recorded `Interrupt` object on the
pending task as a side effect, even though `awaiting_approval` hasn't
actually re-run yet. Checking `task.interrupts` after a selection call
would therefore incorrectly report `waiting_for_approval: false`.
`_is_waiting_for_approval()` checks `snapshot.next` instead, which
stays accurate across that write (this graph only ever leaves anything
pending in `next` when it stopped at an interrupt).

---

## 6. Store mode

Unchanged default: `Settings.store_mode = "mock"` (see
`app/core/config.py`), so `GET/POST /v1/requests*` run against Phase
7's deterministic mock adapters unless `STORE_MODE`/`BLINKIT_STORE_MODE`
/etc. env vars say otherwise — this phase adds no new toggle and
changes no defaults.

---

## 7. Manual testing & verification

```bash
cd shopping-agent/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

**Expected:** 346/346 pass (326 pre-existing + 20 new in
`tests/api/test_requests.py`).

```bash
ruff check app/api/v1/endpoints/requests.py app/core/dependencies.py \
  app/graph/nodes/order_execution.py app/graph/nodes/recommendation.py \
  app/graph/state.py app/graph/workflow.py
```

**Expected:** clean.

### Try it live

```bash
uvicorn app.main:app --reload
```

```bash
curl -X POST localhost:8000/v1/requests \
  -H 'content-type: application/json' \
  -d '{"raw_text": "I need onions, cheapest"}'
# -> {"thread_id": "...", "waiting_for_approval": true, "recommendation": {...}, ...}

curl localhost:8000/v1/requests/<thread_id>

curl -X POST localhost:8000/v1/requests/<thread_id>/approval \
  -H 'content-type: application/json' \
  -d '{"decision": "approved"}'
# -> {"status": "ready_for_payment", "ready_for_payment": true, ...}
```

(Real intent extraction needs Ollama reachable per `OLLAMA_BASE_URL`;
without it, `POST /v1/requests` will 500 from the LLM connection error
— same as any other Phase 4+ code path, unrelated to this phase.)

---

## 8. Known limitations

- Single-process only: `InMemorySaver` does not survive a restart or
  scale across multiple worker processes — acceptable for this phase's
  "no database in MVP" scope, called out explicitly rather than
  silently assumed.
- `POST /{thread_id}/selection`'s index validation checks against the
  full cross-store candidate list length as a permissive upper bound
  (the true per-store bound isn't knowable without first computing
  which store wins); `select_best_store` itself silently falls back to
  index 0 if a given store's own candidate list is shorter than the
  supplied index. Not a new limitation — inherited from the existing
  Phase 15(2) function.
- `order_execution_node`'s checkout-failure branch (distinct from its
  cart-failure branch) doesn't set `error_message` in `GraphState`; the
  API response layer substitutes `order_confirmation.message` in that
  case rather than the generic terminal-node fallback text. A
  response-shaping choice, not a change to graph/node state.
