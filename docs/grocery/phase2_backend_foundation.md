# Phase 2 — Backend Foundation

> **Status:** First runnable code. FastAPI app, configuration, DI, logging, one endpoint.
> **Not yet:** LLM integration (Phase 3), LangGraph (Phase 5), any adapter (Phase 7+).

---

## 1. Goal

Stand up the thinnest possible *real* backend: an app that starts, loads
config correctly, logs in a structured way, and answers one endpoint —
proving the whole `api → core` seam works before anything reasoning-related
is layered on top.

---

## 2. Concepts to Learn From This Phase

- **Application factory pattern** (`create_app()`) vs. a bare module-level
  `FastAPI()` instance, and why the former is what makes an app testable.
- **FastAPI's `Depends()`** as a full dependency-injection mechanism —
  no third-party DI framework is required for a project this size.
- **`lru_cache`-based singletons** as a lightweight alternative to a
  hand-rolled container/registry.
- **Structured (JSON) logging** and why "logging" and "printing" are
  different disciplines in a system with concurrent async requests.
- **API versioning by router composition**, not by conditionals inside
  route handlers.

---

## 3. Architecture Fit

This phase implements exactly the `api/` and `core/` boxes from Phase 0 §2
and §9 — nothing below them. `core/` has zero dependencies on anything else
in `app/` (as required by the acyclic dependency graph); `api/` depends only
on `core/`. No file created this phase imports from `agents/`, `graph/`,
`adapters/`, `automation/`, or `processing/` — those don't exist yet.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py            **Settings + get_settings()**
│   │   ├── logging.py            **JsonFormatter + setup_logging()/get_logger()**
│   │   └── dependencies.py       **DI seams (re-exports + get_app_logger)**
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          **aggregates all v1 routers**
│   │       └── endpoints/
│   │           └── health.py       **GET /v1/health**
│   └── main.py                    **create_app() + module-level app**
└── tests/
    ├── core/test_config.py         **new**
    └── api/test_health.py           **new**
```

---

## 5. File-by-File Explanation

### `app/core/config.py`
Defines `Settings(BaseSettings)` — every config key from `.env.example`
(Phase 1), now typed and validated. `app_env` is a `Literal["local", "test",
"production"]` rather than a bare `str`, so a typo like `APP_ENV=locl` fails
fast at startup instead of silently misbehaving later.

`get_settings()` is `lru_cache`-wrapped: the *first* call constructs and
validates a `Settings()`; every subsequent call in the process returns the
same instance. This is the entire "singleton" story — no custom registry
needed.

**Why not read `os.environ` directly in each module that needs a value?**
Because that scatters config concerns across the codebase and makes it
impossible to override configuration cleanly in tests — every module would
need its own monkeypatch.

### `app/core/logging.py`
`JsonFormatter` is a ~15-line `logging.Formatter` subclass that renders each
record as one JSON line, automatically merging in any `extra={...}` fields a
caller supplies (this is how `request_id`, `graph_node`, etc. will get
attached starting in later phases, without this formatter needing to know
about them ahead of time).

`setup_logging(settings)` configures the *root* logger once, at app
startup — clearing any pre-existing handlers first so re-calling it (e.g.
once per test) never causes duplicate log lines.

`get_logger(name)` is a one-line wrapper over `logging.getLogger`. It looks
almost pointless today — that's intentional. It exists so that if the
logging backend is ever swapped (e.g. for `structlog`), there's exactly one
place to change, not N call sites.

### `app/core/dependencies.py`
The project's entire "DI container." Re-exports `get_settings` and adds
`get_app_logger()`, both meant to be used as `Depends(...)` in route/service
signatures. As `agents/`, `graph/`, and `adapters/` come online in later
phases, their factories (e.g. `get_ollama_client()`, `get_langgraph_app()`)
get added here too — this file is the one seam every later phase's DI
extends, never bypasses.

### `app/api/v1/endpoints/health.py`
A single `GET /health` route (mounted at `/v1/health` by the router
aggregator). Returns `status`, `app_name`, `app_version`, `environment` —
enough to confirm the process is alive and configuration loaded correctly.
Deliberately checks *nothing* downstream (no Ollama ping, no Appium check)
— a health check that depends on flaky downstream systems becomes useless
the moment any one of them hiccups. Per-dependency readiness checks are a
reasonable future addition (see §10), kept separate from this basic
liveness probe.

### `app/api/v1/router.py`
One `APIRouter` that every `v1` endpoint module registers into. `main.py`
mounts this single router under `/v1` — meaning **the only place the
`/v1` prefix is written is `main.py`**. Adding `/v2` later means creating a
parallel `api/v2/router.py` and mounting it alongside; existing `/v1`
consumers are untouched.

### `app/main.py`
`create_app(settings=None)` is the application factory:

1. Resolves which `Settings` to use (explicit, for tests — or the cached
   singleton, for real runs).
2. Calls `setup_logging()`.
3. Builds the `FastAPI` instance with a `lifespan` context manager that
   logs structured startup/shutdown events (the modern replacement for
   FastAPI's older `@app.on_event("startup")` decorators).
4. If explicit test settings were passed, registers a
   `dependency_overrides` entry so every `Depends(get_settings)` in the
   app resolves to *that* instance — not the process-wide cached one.
5. Mounts the `/v1` router.

The module-level `app = create_app()` at the bottom exists solely so
`uvicorn app.main:app` has something to import — application code should
otherwise always go through the factory, never touch this module-level
instance directly (which is why the tests below never import it).

---

## 6. Testing

### `tests/core/test_config.py`
Verifies defaults apply with no environment overrides, verifies environment
variables do override defaults, and verifies case-insensitive env-var
matching. Constructs `Settings(_env_file=None, ...)` directly rather than
via `get_settings()`, so these tests never touch the `lru_cache` singleton
or a real `.env` file.

### `tests/api/test_health.py`
Uses `create_app(settings=test_settings)` + FastAPI's `TestClient` to hit
`/v1/health` against fully controlled, isolated config. Three tests:
status code, exact response shape, and — importantly — that the
*unversioned* `/health` path returns `404`, which is what actually proves
the versioning is enforced by router mounting rather than by convention.

---

## 7. Manual Testing & Verification

> Run these on your machine, where the Phase 1 `pip install` already
> succeeded — this sandbox has no network access to install packages, so
> everything above was syntax-checked with `py_compile` but not
> runtime-executed here.

### Setup (if not already done from Phase 1)

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run the automated tests

```bash
pytest tests/core/test_config.py tests/api/test_health.py -v
```

**Expected:** 6 tests pass (3 in `test_config.py`, 3 in `test_health.py`).

### Run the app for real

```bash
uvicorn app.main:app --reload
```

**Expected console output** (structured JSON, one line):
```json
{"timestamp": "...", "level": "INFO", "logger": "app.startup", "message": "application_startup", "app_env": "local", "app_version": "0.1.0"}
```

### Hit the health endpoint

```bash
curl -s http://localhost:8000/v1/health | python3 -m json.tool
```

**Expected:**
```json
{
    "status": "ok",
    "app_name": "Intent-to-Action Shopping Agent",
    "app_version": "0.1.0",
    "environment": "local"
}
```

### Confirm versioning is enforced

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
```
**Expected:** `404`

### Confirm interactive docs work (free FastAPI feature, good sanity check)

Open `http://localhost:8000/docs` in a browser — should show the Swagger UI
with `/v1/health` listed.

---

## 8. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` on startup mentioning `app_env` | `.env` has an invalid value like `APP_ENV=dev` (not one of `local/test/production`) | Fix the value in `.env` to a valid literal. |
| `ModuleNotFoundError: No module named 'app'` running `uvicorn` | Run from `backend/`, not the repo root | `cd backend` first. |
| `/v1/health` returns `404` | Router not mounted, or wrong prefix | Confirm `main.py` calls `app.include_router(api_router, prefix="/v1")`. |
| Log lines print twice | `setup_logging()` called more than once without going through `create_app()` | Only ever configure logging via `create_app()`/`setup_logging()`, once. |
| Tests fail with `Settings` picking up your real `.env` values | Test forgot `_env_file=None` | Always pass `_env_file=None` when constructing `Settings` directly in tests. |

---

## 9. Edge Cases Considered

- **Missing `.env` file entirely:** `Settings()` still works — every field
  has a default, so a completely bare environment is a valid (if minimal)
  configuration. This matters for CI environments that won't have a
  `.env`.
- **Two different `Settings` instances in one test run:** handled by the
  `dependency_overrides` mechanism in `create_app()` — each test's app
  instance is fully isolated from the cached singleton and from other
  tests.
- **Re-importing `app.main` multiple times in a test session:** the
  module-level `app = create_app()` only runs once per process (Python
  module caching), so tests deliberately avoid depending on it and build
  fresh instances instead.

---

## 10. Acceptance Criteria

- [ ] `pytest tests/core/test_config.py tests/api/test_health.py -v` — 6/6 pass.
- [ ] `uvicorn app.main:app --reload` starts without error and logs a
      structured JSON startup line.
- [ ] `GET /v1/health` returns `200` with the exact shape shown in §7.
- [ ] `GET /health` (unversioned) returns `404`.
- [ ] `/docs` renders and lists the health endpoint.

Only once every box is checked should Phase 3 (LLM layer) begin.

---

## 11. Verification Checklist

- [x] All new files pass `py_compile` (verified in this environment).
- [ ] All 6 tests pass on your machine (needs network-installed deps — verify locally).
- [ ] App starts and serves `/v1/health` correctly (verify locally).
- [x] No file in this phase imports from `agents/`, `graph/`, `adapters/`, `automation/`, or `processing/` — dependency graph from Phase 0 §9 respected.
- [x] `core/` has zero dependencies on `api/` (checked by inspection — `config.py`, `logging.py`, `dependencies.py` import nothing from `app.api`).

---

## 12. Known Limitations

- The health check is a pure liveness probe — no readiness signal for
  Ollama/Appium availability yet, since neither exists as a dependency
  until Phase 3/6.
- No request-ID middleware yet — the `request_id` correlation field
  described in Phase 0 §13 has a slot ready in `JsonFormatter` (via
  `extra={}`) but nothing populates it until Phase 4/5 introduce actual
  requests flowing through the graph.
- `Settings` validation is type/literal-based only — no cross-field
  validation (e.g. "if `app_env=production`, `log_level` cannot be
  `DEBUG`") is implemented; add if/when that becomes a real operational
  concern.

## 13. Improvements to Consider Later

- Add a `/v1/health/ready` endpoint once there are real downstream
  dependencies (Ollama, Appium) worth checking.
- Add request-ID middleware (generate or propagate a correlation ID per
  request, attach via `extra={"request_id": ...}` to every log line in
  that request's lifecycle) once Phase 4 introduces real request handling.
- Consider `structlog` if/when concurrent multi-agent logging makes
  manual `extra={}` dictionaries unwieldy.

---

## Next Step

Once the Manual Testing Guide (§7) passes on your machine, say
**"Move to Phase 3"** to begin the LLM layer — Ollama/Qwen integration, the
prompt manager, and structured JSON output validation.
