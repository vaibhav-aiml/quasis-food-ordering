# Phase 3 — LLM Layer

> **Status:** Ollama/Qwen integration, prompt management, structured JSON
> output with Pydantic validation and retry — fully generic infrastructure.
> **Not yet:** anything that knows what "intent" or "product" means — that's
> Phase 4. This phase never mentions biryani, onions, or shopping.

---

## 1. Goal

Give every future agent (Intent Understanding, Planning, Recommendation) one
reliable way to ask the LLM for structured data and get back a *validated
Pydantic object*, never a raw string to parse by hand. Get the retry and
error-handling policy right once, here, so no agent reimplements it.

---

## 2. Concepts to Learn From This Phase

- **`typing.Protocol`** for structural typing — why `LLMClient` doesn't need
  an abstract base class, and how this lets tests avoid a mocking library.
- **Schema-constrained decoding** vs. plain "JSON mode" — Ollama can
  constrain generation to match a JSON schema exactly, which is materially
  more reliable than just asking nicely for JSON.
- **Why `str.format()`/f-strings are actively dangerous for prompt
  templates** that embed JSON schemas, and why `string.Template`'s
  `$variable` syntax avoids the collision.
- **Multi-turn self-correction**: feeding a model its own invalid output
  plus the specific validation error, as a repair strategy.
- **Retry policy design**: how many attempts, what changes between
  attempts, and what exception surfaces when retries are exhausted.

---

## 3. Architecture Fit

Implements the `agents/`-adjacent infrastructure that sits under `core/`,
per Phase 0's dependency graph — `core/llm/` depends only on `core/config.py`
and third-party libraries, and nothing in `api/`, `graph/`, or future
`agents/` code talks to Ollama directly. Everything goes through
`StructuredLLMService`, injected via `core/dependencies.py`, exactly like
`Settings` and the logger in Phase 2.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/core/
├── llm/
│   ├── __init__.py
│   ├── exceptions.py               **LLMError / LLMConnectionError / LLMValidationError**
│   ├── client.py                    **LLMClient protocol + OllamaLLMClient**
│   ├── prompts.py                    **PromptManager**
│   ├── structured.py                  **StructuredLLMService**
│   └── prompt_templates/
│       └── example_ping.txt            **demo template**
└── dependencies.py                  **+3 new factories**

backend/tests/core/
├── test_prompts.py                  **new**
└── test_llm_structured.py           **new**
```

---

## 5. File-by-File Explanation

### `app/core/llm/exceptions.py`
Three exceptions: `LLMError` (base), `LLMConnectionError` (backend
unreachable — nothing to retry against), `LLMValidationError` (model
responded but never produced valid output, even after retries — carries
`raw_response`, `validation_errors`, and `attempts` for debugging).

### `app/core/llm/client.py`
`LLMClient` is a `Protocol` — one method, `chat()`. `OllamaLLMClient` is the
concrete implementation, built around the real `ollama` Python library's
documented API (`ollama.Client(host=...).chat(model=..., messages=...,
format=schema)`, verified against Ollama's own docs during this phase's
design). It passes the Pydantic model's JSON schema directly as the
`format` parameter — Ollama's schema-constrained decoding — rather than
the older, less reliable `format="json"` string mode.

**Why a `Protocol` instead of an abstract base class:** any object with a
matching `chat()` method satisfies `LLMClient` — no inheritance chain to
build. `FakeLLMClient` in the tests is a completely standalone class that
happens to match the shape; nothing links it to `OllamaLLMClient`.

### `app/core/llm/prompts.py`
`PromptManager` loads `.txt` files from `prompt_templates/` and renders
them via `string.Template.substitute(**variables)`.

**The bug I found and fixed while verifying this phase:** the first
version of `render()` had its "which template to load" parameter named
`name`, which collided head-on with any template that itself needed a
`$name` variable (`TypeError: got multiple values for argument 'name'`). I
caught this by actually running the code against a real template, not just
`py_compile`-checking it — renamed the parameter to `template_name`. Worth
flagging explicitly since it's exactly the kind of bug that silent,
unverified code review misses.

Uses `Template.substitute()` (not `safe_substitute()`) deliberately — a
missing variable should be a loud `KeyError` at render time, not a prompt
silently sent to the model with a literal `$foo` still in it.

Templates are cached in a dict after first load — a template's content is
fixed for the process lifetime; editing the `.txt` file requires a process
restart to take effect (documented and tested).

### `app/core/llm/structured.py`
`StructuredLLMService.generate()` is the single public entry point for
structured LLM calls:

1. Renders the prompt (auto-injecting `schema` as the target model's JSON
   schema — callers never pass `schema` themselves).
2. Calls the client with that schema also passed as the native `format`
   constraint.
3. Parses JSON, then validates via `response_model.model_validate(data)`.
4. On JSON-parse failure *or* Pydantic `ValidationError`, appends the bad
   assistant turn plus a corrective user turn to the conversation and
   retries — up to `max_retries` additional attempts (default 2, so 3
   total attempts).
5. Raises `LLMValidationError` with full context if still invalid.

Note this method is fully generic over `response_model` — it has never
seen `IntentRequest` or any shopping-domain type. Phase 4 will call this
with its own Pydantic models; this file doesn't change.

### `app/core/dependencies.py` (additions)
Three new `lru_cache`-wrapped factories: `get_llm_client()`,
`get_prompt_manager()`, `get_structured_llm_service()`. Agent code in
Phase 4 should depend on `get_structured_llm_service()` — not
`get_llm_client()` directly — since that's the layer with validation and
retry built in.

---

## 6. Testing

### `tests/core/test_prompts.py`
5 tests, all runtime-verified in this environment (pure stdlib, no
external packages needed): variable substitution, the exact brace-collision
case that motivated choosing `string.Template`, missing-template error,
missing-variable error, and caching behavior.

### `tests/core/test_llm_structured.py`
5 tests using `FakeLLMClient` — a hand-written class satisfying the
`LLMClient` protocol, returning a scripted sequence of raw responses per
call. Covers: first-attempt success, recovery after invalid JSON, recovery
after a schema validation failure, exhausting all retries and raising
`LLMValidationError`, and confirming the Pydantic schema is actually passed
as `response_format`.

**This file needs `pydantic` installed to run — it wasn't executed in this
sandbox** (no network access here to install packages), only
`py_compile`-checked for syntax. Run it for real per §7 below.

---

## 7. Manual Testing & Verification

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt   # if not already done

pytest tests/core/test_prompts.py tests/core/test_llm_structured.py -v
```

**Expected:** 10 tests pass (5 + 5).

### Optional: exercise it against a real running Ollama

If you have Ollama running locally with the configured model pulled:

```bash
ollama pull qwen2.5:7b-instruct   # if not already pulled
ollama serve                       # if not already running
```

```python
# Run from `backend/` with the venv active: python3
from pydantic import BaseModel
from app.core.dependencies import get_structured_llm_service

class PingResponse(BaseModel):
    reply: str
    confidence: float

service = get_structured_llm_service()
result = service.generate(
    template_name="example_ping",
    response_model=PingResponse,
    variables={"user_message": "Say hello and rate your confidence 0-1."},
)
print(result)
```

**Expected:** a `PingResponse(reply=..., confidence=...)` instance —
proving the full pipeline (prompt render → Ollama call → schema-constrained
generation → JSON parse → Pydantic validation) works end-to-end against a
real model, not just the fake client.

**This step requires Ollama installed and running — it's optional for
Phase 3 approval** but strongly recommended before Phase 4 builds real
agents on top of this.

---

## 8. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `LLMConnectionError: Failed to reach Ollama...` | Ollama isn't running, or `OLLAMA_BASE_URL` in `.env` is wrong | `ollama serve` in another terminal; confirm the URL matches (`http://localhost:11434` by default). |
| `LLMValidationError` even with a real model | Model genuinely can't produce the schema reliably, or the prompt template needs tuning | Inspect `exc.raw_response` and `exc.validation_errors` (both attached to the exception) to see exactly what the model produced and why it failed. |
| `KeyError` when rendering a template | A `$variable` in the `.txt` file wasn't supplied in `variables=` | Check the template file for all `$name`-style placeholders and supply each one. |
| `TypeError: got multiple values for argument` | (Should no longer happen — this was the bug fixed in §5. If you see it again, check for a similarly-named collision.) | Rename the colliding parameter/variable. |
| Ollama responds but very slowly with schema constraints | Known behavior with some model/schema combinations (documented in Ollama's own issue tracker) | Consider a smaller/simpler schema, or accept the latency for correctness — don't fall back to unconstrained JSON mode without discussing the tradeoff. |

---

## 9. Edge Cases Considered

- **Model returns valid JSON but wrong types** (e.g. `confidence` as a
  string `"0.9"` instead of a float) — caught by Pydantic's
  `ValidationError`, triggers the same retry path as a missing field.
- **Model wraps JSON in markdown code fences** (`` ```json ... ``` ``) —
  will fail `json.loads()` and trigger a retry with an explicit instruction
  not to use code fences. Not yet stripped automatically — flagged as a
  possible future improvement if this proves common in practice (see §12).
- **Retries exhausted on a connection-level failure mid-way through the
  loop** — not applicable: `LLMConnectionError` isn't caught by the retry
  loop at all, since `client.chat()` raising it propagates immediately.
  Retries only apply to *parsing/validation* failures, not connectivity
  failures — a connectivity failure retried 3 times would just be 3x the
  latency for the same outcome.

---

## 10. Acceptance Criteria

- [ ] `pytest tests/core/test_prompts.py tests/core/test_llm_structured.py -v` — 10/10 pass.
- [ ] (Optional but recommended) the live Ollama script in §7 produces a valid `PingResponse`.
- [ ] No file under `app/core/llm/` references anything shopping/intent/product-specific.

---

## 11. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] `PromptManager` runtime-verified in this sandbox (stdlib-only, no
      external deps needed) — including the brace-collision case and the
      parameter-naming bug found and fixed during verification.
- [ ] `test_llm_structured.py` (needs `pydantic`) — run locally to confirm.
- [x] `core/llm/` has no dependency on `api/`, `graph/`, `agents/`, `adapters/`, `automation/`, or `processing/` — dependency graph respected.
- [x] `StructuredLLMService.generate()` is fully generic — no domain-specific type appears anywhere in `structured.py`.

---

## 12. Known Limitations

- Ollama's specific exception types (e.g. `ollama.ResponseError`) aren't
  caught individually — `OllamaLLMClient.chat()` wraps *any* exception from
  the underlying client into `LLMConnectionError`. This is safe but coarse;
  worth narrowing once this has been exercised against a real server and
  the actual exception surface is observed firsthand.
- No automatic stripping of markdown code fences around JSON — relying on
  the retry loop's corrective instruction instead. Revisit if this proves
  to be a frequent failure mode with the actual Qwen model in practice.
- `max_retries` is a constructor-level default (2), not currently
  configurable per-call. Fine for now since Phase 4's agents are expected
  to have broadly similar reliability needs — split if that assumption
  turns out wrong.
- No token/cost tracking or timeout configuration yet — not needed for a
  local Ollama backend, but would matter if a hosted API backend is ever
  swapped in (§ design decisions, Phase 0).

## 13. Improvements to Consider Later

- Strip common wrapping patterns (markdown fences, leading/trailing
  prose) from raw responses before attempting `json.loads()`, if that
  proves to be a real failure mode.
- Narrow `OllamaLLMClient`'s exception handling to Ollama's actual
  exception types once observed against a running server.
- Add a request timeout to `OllamaLLMClient.chat()` — currently relies on
  whatever default the underlying `ollama.Client` uses.
- Consider making `max_retries` a parameter on `generate()` itself if
  different agents end up needing meaningfully different retry budgets.

---

## Next Step

Once `pytest` passes locally (and ideally the live Ollama check too), say
**"Move to Phase 4"** to build the Intent Understanding Agent — the first
real consumer of `StructuredLLMService`, extracting products and
constraints from free text like "I'm making biryani, need onions and curd,
cheapest option under 20 minutes."
