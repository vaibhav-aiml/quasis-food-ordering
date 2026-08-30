# Phase 1 — Project Planning & Setup

> **Status:** Scaffolding only. Empty packages, config skeleton, dev environment.
> No FastAPI app, no LangGraph code, no adapter logic — that begins Phase 2 onward.

---

## 1. Goal

Turn the Phase 0 architecture into a real, checked-out repository skeleton that
every later phase writes *into*, rather than argues about. By the end of this
phase, a new contributor can clone the repo, set up their environment, and
verify it's healthy — before a single feature line of code exists.

---

## 2. Final Architecture Review

No changes since Phase 0. The folder structure below is a direct, unmodified
implementation of §8 (Folder Structure) and §9 (Dependency Graph) from
`docs/phase0_architecture.md`. If you want to revise the architecture, that
should happen by editing Phase 0's document first — Phase 1 is not the place
to redesign, only to instantiate.

---

## 3. Development Workflow

- **One phase, one commit (or small commit series) with a clear message**, e.g.
  `phase-2: fastapi foundation + health endpoint`. Since the master process
  requires explicit approval before advancing, phase boundaries are natural
  commit boundaries — this makes `git log` double as a build history that
  matches the docs.
- **`main` is always runnable.** Nothing merges into `main` that fails the
  manual verification checklist of its own phase. There's no CI yet (local-only
  MVP per the stack decision), so this is a discipline rule, not an enforced
  gate — worth automating with GitHub Actions once/if this leaves local dev.
- **Docs live with the code they describe.** Each phase's design doc lands in
  `docs/phaseN_*.md` alongside the phase's implementation commit, not written
  up separately afterward — keeps the docs from drifting out of sync.
- **No feature branches for solo/tutorial-style development at this scale** —
  branching overhead isn't justified for a single-contributor phased build
  (rule #8, avoid overengineering). Revisit if this becomes a team project.

---

## 4. Folder Structure (created this phase)

```
quasis-food-ordering/
├── backend/
│   ├── app/
│   │   ├── core/            # config, DI container, logging — empty until Phase 2
│   │   ├── automation/      # Swiggy uiautomator2 automation
│   │   ├── food_ordering/   # food ordering domain models
│   │   ├── shared/          # shared utilities
│   │   └── grocery/         # Quick-commerce grocery agent
│   │       ├── api/v1/          # FastAPI routers — empty until Phase 2
│   │       ├── domain/          # Pydantic entities — empty until Phase 4/10
│   │       ├── agents/          # LLM-backed reasoning — empty until Phase 3/4
│   │       ├── graph/nodes/     # LangGraph state & nodes — empty until Phase 5
│   │       ├── adapters/{zepto,blinkit,instamart}/  # empty until Phase 7
│   │       ├── automation/      # Appium layer — empty until Phase 6
│   │       ├── processing/      # verification/normalization/ranking — empty until Phase 9-11
│   │       ├── services/        # tool orchestrator — empty until Phase 5
│   │       └── prompts/         # LLM prompt templates
│   ├── tests/               # mirrors backend/app structure
│   │   ├── automation/
│   │   ├── core/
│   │   └── grocery/         # mirrors app/grocery/ 1:1
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── apps/mobile/             # React Native / Expo mobile client
├── services/backend/        # Fastify / SSE TypeScript backend
├── docs/grocery/            # grocery architecture & phase docs
├── .gitignore
└── README.md
```

### Why each top-level folder exists

| Folder | Reason |
|---|---|
| `backend/` | Isolates the Python application from the Flutter client and docs — each has its own dependency ecosystem and shouldn't share a root-level config. |
| `mobile/` | Reserved now so the top-level layout matches the architecture diagram from day one, even though it's empty until the API contract stabilizes. |
| `docs/` | Every phase's design doc lives here permanently — the repo becomes self-documenting instead of relying on external notes that go stale. |

### Why each `app/` subfolder exists

This is a direct restatement of Phase 0 §9's dependency graph, made physical:

| Folder | Reason it's separate from its neighbors |
|---|---|
| `api/` | The only layer allowed to know about HTTP (FastAPI request/response). Keeping this thin and separate means the business logic underneath is testable without spinning up a server. |
| `core/` | Cross-cutting infrastructure (settings, DI wiring, logging setup) that every other layer may depend on, but which depends on nothing else — matches rule #7 and the acyclic dependency graph. |
| `domain/` | Framework-agnostic Pydantic models. Deliberately has **zero** dependencies on any other `app/` folder, so it can be imported anywhere without risk of circular imports. |
| `agents/` | LLM-backed reasoning only. Isolated from `processing/` specifically so it's obvious, just from folder placement, that nothing in here is allowed to make a ranking decision (master rule #1 vs #2). |
| `graph/` | LangGraph state/node/edge definitions — the orchestration layer that calls into `agents/`, `services/`, but is called only by `api/`. |
| `adapters/` | One subfolder per store, behind a shared interface (`base.py`, added Phase 7) — enforces master rules #5/#6. |
| `automation/` | Appium mechanics only — no store-specific or business logic, so it's reusable across all three adapters unchanged. |
| `processing/` | Deterministic verification/normalization/ranking — separated from `agents/` for the same reason as above, just from the other side. |
| `services/` | Orchestration glue (e.g., the Tool Orchestrator) that coordinates `adapters/` + `processing/` on behalf of `graph/` nodes, without those nodes needing to know adapter details directly. |

`tests/` mirrors `app/` folder-for-folder so any file's tests are one directory
away, and so `pytest --cov` output maps cleanly back to source layout.

---

## 5. Configuration Strategy

- `.env.example` (committed) documents every config key the project will need,
  grouped by concern (App / LLM / Appium / Future). `.env` (gitignored) holds
  real local values.
- The actual `Settings` class (Pydantic `BaseSettings`) that reads these values
  is **Phase 2 work**, not Phase 1 — this phase only fixes the *shape* of
  configuration so Phase 2 has a stable target to code against.
- Config keys already anticipate Phase 17-19 extension points (`DATABASE_URL`,
  `REDIS_URL` present but commented out) so adding persistence later doesn't
  require renegotiating the config file format.

---

## 6. Dependency Management

**Decision: `pip` + `requirements.txt`/`requirements-dev.txt` + standard `venv`.**

| Considered | Verdict | Reasoning |
|---|---|---|
| `pip` + `requirements.txt` | **Chosen** | No extra tool to install, every Python dev already knows it, matches "local development only" scope from the stack decision. Split into runtime vs. dev files so a future production install doesn't pull test tooling. |
| Poetry | Rejected (for now) | Better lockfile/resolution guarantees and packaging metadata, but adds tooling overhead not justified for a single-developer local MVP. Reasonable to switch to once this is packaged/distributed. |
| `uv` | Rejected (for now) | Excellent speed and increasingly standard, but less universally pre-installed; `pip` minimizes onboarding friction, which matters most while you're still learning the stack. |
| Conda | Rejected | Pulls in a much heavier environment manager than a pure-Python, no-native-dependency project needs. |

Versions in `requirements.txt` are pinned to `major.minor` ranges, not exact
patches — tight enough to avoid breaking changes, loose enough that security
patches aren't blocked. Exact resolved versions will be visible in whatever
`pip freeze` produces once Phase 2's venv is built — worth committing a
`requirements.lock.txt` at that point if reproducibility becomes important.

---

## 7. Local Development Setup

```bash
git clone <repo-url> quasis-food-ordering
cd quasis-food-ordering/backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
cp .env.example .env
```

At this point there is **no application to run** — that's correct for Phase 1.
Verification below confirms the environment itself is sound.

---

## 8. Manual Testing & Verification

### Manual Testing Guide

1. Run the setup commands in §7 exactly as written.
2. Confirm the venv activated: prompt should show `(.venv)`.
3. Confirm dependencies installed cleanly:
   ```bash
   pip list | grep -E "fastapi|langgraph|pydantic|Appium"
   ```
   Expected: all four appear with the versions pinned in `requirements.txt`.
4. Confirm the package structure imports without error:
   ```bash
   python -c "import app; import app.api; import app.core; import app.domain; \
   import app.agents; import app.graph; import app.adapters; import app.automation; \
   import app.processing; import app.services; print('all packages import cleanly')"
   ```
   Run from inside `backend/`. Expected output: `all packages import cleanly`.
5. Confirm `.env` exists and is gitignored:
   ```bash
   git status --ignored | grep .env
   ```
   Expected: `.env` listed under ignored files, **not** under tracked changes.

### Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Not running from `backend/`, or venv not active | `cd backend && source .venv/bin/activate` |
| `pip install` fails on `Appium-Python-Client` | Missing system-level build tools on some platforms | Usually resolves with `pip install --upgrade pip setuptools wheel` first |
| `.env` shows up in `git status` as untracked/trackable | `.gitignore` not picked up (rare caching issue) | `git rm -r --cached .` then re-add, or verify `.gitignore` is at repo root, not inside `backend/` |

### Edge Cases

- Running setup on Windows: activation command differs (`.venv\Scripts\activate`) — documented above.
- Python version mismatch: this project assumes Python 3.11+ (Pydantic v2 + modern typing features used from Phase 4 onward); no version pin enforced yet — worth adding a `.python-version` file if this becomes a recurring issue.

### Acceptance Criteria

- [ ] `git clone` + setup commands complete without error.
- [ ] All four key dependencies present at pinned versions.
- [ ] All nine `app/` subpackages import successfully with zero errors.
- [ ] `.env` is gitignored and not accidentally trackable.
- [ ] Folder structure on disk matches §4 of this document exactly.

Only once every box above is checked should Phase 2 begin.

---

## 9. Verification Checklist

- [x] Repository skeleton created matching Phase 0 §8.
- [x] Every `app/` and `tests/` subpackage has an `__init__.py`.
- [x] `requirements.txt` / `requirements-dev.txt` present and split correctly.
- [x] `.env.example` documents all currently-known config keys.
- [x] `.gitignore` covers Python, env files, Appium artifacts, IDE, OS, and Flutter build output.
- [x] `README.md` gives a working quickstart.
- [ ] **You** run the Manual Testing Guide (§8) on your machine and confirm it passes.

---

## 10. Improvements to Consider Later

- Add a `Makefile` or `justfile` once the number of repeated commands (install, lint, test, run) grows past 2–3 — premature right now (rule #8).
- Add a `requirements.lock.txt` (via `pip freeze`) once the dependency set stabilizes, for byte-for-byte reproducible installs.
- Add a pre-commit hook (ruff + mypy) once there's actual code to lint — no value running it against empty packages.
- Revisit Poetry/`uv` if this project ever needs to be distributed as an installable package rather than run from source.

---

## Next Step

Once you've run the Manual Testing Guide (§8) and everything checks out, say
**"Move to Phase 2"** to begin the FastAPI backend foundation — configuration
loading, dependency injection, logging, and the health endpoint.
