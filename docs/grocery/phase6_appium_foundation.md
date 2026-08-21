# Phase 6 — Appium Foundation

> **Status:** The automation layer's mechanics — session lifecycle, waits,
> gestures, screenshots — fully built and unit-tested against fakes. No
> real store automation yet; that's Phase 7 (adapters) and Phase 8 (wiring
> adapters to real Appium calls).

---

## 0. Dependency pins fixed proactively, before writing any code

Before touching Phase 6, I verified the actual current `Appium-Python-Client`
API against its documentation and PyPI release history (given the last two
issues both traced back to unverified library assumptions, this seemed
worth doing preemptively rather than waiting for a live failure a third
time). Found the same class of problem already latent in `requirements.txt`:

- `Appium-Python-Client>=4.1,<5.0` → **`>=5.1,<6.0`**. PyPI shows the
  current stable release is `5.3.1` (Apr 2026); the `<5.0` ceiling excluded
  the entire current major version, including a documented v4→v5 migration
  affecting `webdriver.Remote()`'s connection arguments.
- Added `selenium>=4.26,<5.0` explicitly. It was previously only an
  implicit transitive dependency of `Appium-Python-Client`, but this
  phase's code imports directly from `selenium.webdriver.support` — an
  explicit dependency for something explicitly imported is the correct
  call per the project's dependency-management principles (Phase 1 §6).

This was caught by checking documentation before writing code, not by a
live test failure — worth noting as the pattern to keep applying before
each phase that leans on a fast-moving external library.

---

## 1. Goal

Build the mechanical layer everything in Phase 7/8 sits on top of:
starting/stopping/restarting an Appium session, waiting for elements
reliably, basic tap/type/scroll primitives, and screenshot capture for
debugging — all typed, DI-friendly, and unit-testable without a real
device or Appium server.

---

## 2. Concepts to Learn From This Phase

- **Composition over inheritance for `DriverManager`** — Store Adapters
  (Phase 7) will each *hold* one, never subclass it.
- **Deferred imports as a testability pattern** — `appium`/`selenium`
  imports live inside functions, not at module top, the same technique
  already used for `ollama` in Phase 3. This is what let every piece of
  this phase be verified in this sandbox without either package installed.
- **Explicit waits vs. `time.sleep()`** — why polling conditions
  (`WebDriverWait` + `expected_conditions`) handle real-world load-time
  variance correctly and sleeping doesn't.
- **Best-effort teardown** — `restart()`'s `try/except/pass` around
  `driver.quit()` is deliberate: a session you're restarting *because* it
  crashed may not tear down cleanly, and that's fine — the goal is a
  fresh session, not a clean shutdown of a broken one.

---

## 3. Architecture Fit

Implements `automation/` from Phase 0 §2/§7 — mechanical device
interaction only, zero product/store/business knowledge (master rules #3,
#4). Nothing here imports from `domain/`, `agents/`, `graph/`, or
`adapters/` — verified by inspection. Store Adapters (Phase 7) will be the
only consumers of this layer, exactly per the Phase 0 dependency graph.

---

## 4. Folder Structure (this phase's additions in bold)

```
backend/app/automation/
├── exceptions.py       **AutomationError / AutomationConnectionError / AutomationTimeoutError**
├── driver_manager.py     **DriverManager — start/stop/restart**
├── capabilities.py         **build_android_capabilities()**
├── waits.py                  **wait_for_element / wait_for_element_clickable**
├── gestures.py                 **tap / type_text / scroll_down**
└── screenshots.py                **capture_screenshot()**

backend/tests/automation/
├── test_driver_manager.py    **new**
├── test_capabilities.py        **new**
├── test_waits.py                 **new**
├── test_gestures.py                **new**
└── test_screenshots.py               **new**
```

`app/core/dependencies.py` gets `create_driver_manager()` — deliberately
**not** `@lru_cache`'d, unlike every other factory in that file. A
`DriverManager` wraps one stateful session; there's no single correct
process-wide instance the way there is for `Settings` or a logger.

---

## 5. File-by-File Explanation

### `app/automation/exceptions.py`
`AutomationError` (base), `AutomationConnectionError` (session couldn't
start at all), `AutomationTimeoutError` (a wait expired). Mirrors the
LLM layer's exception design (Phase 3) — callers catch these, never raw
Appium/Selenium exceptions.

### `app/automation/driver_manager.py`
`DriverManager` owns exactly one session's lifecycle. `start()` refuses
to run if a session is already active (an explicit `AutomationError`, not
a silent overwrite — losing a reference to a live session would leak it).
`restart()` implements Phase 0 §12's policy verbatim: best-effort
teardown of the old session (swallowing any exception — the old session
may already be dead), then a fresh `start()`. `_default_driver_factory`
is where the real `appium.webdriver.Remote(...)` call lives, imported
lazily so the class stays testable via an injected fake factory. Supports
`with DriverManager(...) as manager:` for guaranteed cleanup.

### `app/automation/capabilities.py`
`build_android_capabilities(settings, **overrides)` — device/platform
defaults from `Settings`, with any store-specific capabilities (app
package, activity) supplied by the caller. Knows nothing about any
specific store; Phase 7 adapters own that.

### `app/automation/waits.py`
Two functions: `wait_for_element` (present in the tree) and
`wait_for_element_clickable` (present, visible, AND enabled). Both wrap
Selenium's `WebDriverWait`/`expected_conditions`, translating a timeout
into `AutomationTimeoutError` rather than leaking a raw
`TimeoutException`. `Locator = tuple[str, str]` is intentionally generic
over *which* locator strategy (`By.ID`, `AppiumBy.ACCESSIBILITY_ID`,
etc.) produced it — that choice belongs to Phase 7's adapters, not this
layer.

### `app/automation/gestures.py`
`tap`, `type_text`, `scroll_down` — the "basic interaction" this phase's
brief calls for. `scroll_down` computes its scroll bounding box from
`driver.get_window_size()` rather than hardcoded pixels, using the
UiAutomator2 `mobile: scrollGesture` command (parameters verified against
current Appium documentation, not assumed).

### `app/automation/screenshots.py`
`capture_screenshot(driver, label, output_dir)` — filenames are
`{UTC timestamp}_{6-char unique suffix}_{sanitized label}.png`. The
unique suffix (not just the timestamp) exists because two calls in the
same test/run could otherwise collide at coarser clock resolutions than
assumed — caught this exact flakiness risk while writing the test for it
and fixed it before it became a real bug, rather than after.

---

## 6. Manual Testing & Verification

### Unit tests (no device/emulator needed)

```bash
cd shopping-agent/backend
source .venv/bin/activate
pip install -r requirements-dev.txt   # picks up the corrected Appium-Python-Client + selenium pins

pytest tests/automation/ -v
```

**Expected:** 27 tests pass (10 driver_manager + 3 capabilities + 5 waits
+ 5 gestures + 4 screenshots).

### Real device/emulator verification (requires actual setup)

This is the part that genuinely needs hardware or an emulator — no way
around it for an "Appium Foundation" phase, and not something this sandbox
can do for you.

1. **Install and start Appium server:**
   ```bash
   npm install -g appium
   appium driver install uiautomator2
   appium
   ```
2. **Start an Android emulator** (via Android Studio's AVD Manager, or
   `emulator -avd <name>` from the command line) or connect a real device
   with USB debugging enabled (`adb devices` should list it).
3. **Confirm `.env`** has `APPIUM_SERVER_URL` and `ANDROID_DEVICE_NAME`
   matching your setup (defaults from Phase 1's `.env.example` assume
   `emulator-5554` — adjust if yours differs).
4. **Run this smoke-test script** (from `backend/`, venv active):

   ```python
   from app.core.dependencies import create_driver_manager
   from app.automation.capabilities import build_android_capabilities
   from app.core.config import get_settings
   from app.automation.screenshots import capture_screenshot

   settings = get_settings()
   caps = build_android_capabilities(
       settings,
       appPackage="com.android.settings",  # a real, always-installed app
       appActivity=".Settings",
   )

   manager = create_driver_manager(settings)
   driver = manager.start(caps)
   print("Session started:", driver.session_id)

   path = capture_screenshot(driver, "settings_app_open")
   print("Screenshot saved to:", path)

   manager.stop()
   print("Session stopped cleanly.")
   ```

   **Expected:** prints a session ID, opens the Android Settings app on
   the device/emulator, saves a screenshot to `./screenshots/`, and stops
   cleanly with no errors.

---

## 7. Debugging Guide

| Symptom | Likely cause | Fix |
|---|---|---|
| `AutomationConnectionError: Failed to start Appium session...` | Appium server not running, or wrong `APPIUM_SERVER_URL` | Confirm `appium` is running (`curl http://localhost:4723/status`) and `.env` points at the right URL. |
| Session starts but immediately errors about device not found | Emulator not running, or `deviceName`/`udid` mismatch | `adb devices` to confirm the device/emulator is visible; match `ANDROID_DEVICE_NAME` to it. |
| `pip install` fails resolving `Appium-Python-Client` | Old pip/setuptools, or a genuinely incompatible OS/Python version | `pip install --upgrade pip setuptools wheel` first (same fix noted back in Phase 1). |
| `AutomationTimeoutError` on every element wait, even for elements you can see on screen | Wrong locator strategy/value for that app's actual element tree | Use Appium Inspector against the running session to find the correct locator before assuming this layer is broken — very often a locator problem, not a waits.py problem. |
| Screenshots directory not gitignored / accidentally staged | `.gitignore`'s `screenshots/` entry only applies at repo root | Confirm you're calling `capture_screenshot` with a relative `output_dir` under the repo, not an absolute path elsewhere. |

---

## 8. Edge Cases Considered

- **`restart()` on a session that's already dead** — `driver.quit()`
  raising is caught and ignored; tested explicitly
  (`test_restart_survives_a_dead_session_quit_raising`).
- **`start()` called twice without `stop()`** — explicit `AutomationError`
  rather than silently leaking the first session's reference.
- **Element present but disabled** — `wait_for_element_clickable`
  correctly times out rather than returning a non-interactable element
  (tested for both "not enabled" and "not displayed" separately).
- **Screenshot label containing path separators** (e.g. a store name with
  a `/`) — sanitized to underscores so it can never accidentally write
  outside `output_dir` or create unintended subdirectories.

---

## 9. Acceptance Criteria

- [ ] `pytest tests/automation/ -v` — 27/27 pass.
- [ ] The real-device smoke-test script in §6 runs successfully against
      your own Appium server + emulator/device — **this is the part I
      cannot verify from this sandbox at all**, not even indirectly.
- [ ] `app/automation/` contains no import from `domain/`, `agents/`,
      `graph/`, or `adapters/` (grep to confirm).

---

## 10. Verification Checklist

- [x] All new files pass `py_compile`.
- [x] `DriverManager` — every method (start, double-start guard, stop,
      no-op stop, restart with a healthy old session, restart surviving a
      dead session's `quit()` raising, factory-exception wrapping, context
      manager) runtime-verified in this sandbox with a fake driver factory.
- [x] `build_android_capabilities` — defaults and overrides runtime-verified.
- [x] `wait_for_element` / `wait_for_element_clickable` — runtime-verified
      against a **behaviorally faithful stub** of Selenium's
      `WebDriverWait` polling loop (built specifically for this phase,
      since the real `selenium` package isn't installable in this
      offline sandbox) — both the "found" and "times out" paths, for both
      functions.
- [x] `tap` / `type_text` / `scroll_down` — runtime-verified against the
      same stub, including the exact `mobile: scrollGesture` parameter
      shape.
- [x] `capture_screenshot` — runtime-verified: label sanitization,
      directory auto-creation, and filename uniqueness across rapid calls.
- [ ] Real Appium server + device/emulator session — **cannot be verified
      from this environment under any circumstances**; this is the one
      category of Phase 6 testing that is irreducibly your responsibility.

---

## 11. Known Limitations

- `scroll_down` only scrolls the full screen — no "scroll within this
  specific container element" variant yet (`mobile: scrollGesture`
  supports an `elementId` parameter for that; add if/when Phase 7's real
  adapters need it for a specific app's layout).
- No `long_press`, `swipe`, or multi-touch gesture primitives yet —
  intentionally minimal per this phase's "basic interaction" scope; add
  as real store automation (Phase 8) reveals what's actually needed.
- `DriverManager` manages exactly one session; no device-pool or
  concurrent-session management yet (flagged as a future scalability item
  back in Phase 0 §16 — still future, not needed until multiple stores
  are searched in parallel with real automation).
- The `waits.py`/`gestures.py` verification in this sandbox used a
  hand-built stub of Selenium's polling behavior, not the real library —
  a faithful-as-I-could-make-it reproduction of documented `WebDriverWait`
  semantics, but not a substitute for running `pytest tests/automation/`
  for real, which uses the actual `selenium` package.

## 12. Improvements to Consider Later

- Add `elementId`-scoped scrolling once a real app's layout needs it.
- Add a device-pool abstraction if/when parallel store searches need
  concurrent sessions (Phase 0 §16).
- Consider narrowing `_default_driver_factory`'s error handling once
  real Appium server error responses have been observed firsthand (same
  category of improvement flagged for `OllamaLLMClient` back in Phase 3).

---

## Next Step

Once `pytest tests/automation/ -v` passes locally AND the real-device
smoke test in §6 succeeds against your own Appium setup, say
**"Move to Phase 7"** to build the Store Adapter Framework — the base
adapter interface plus Zepto/Blinkit/Instamart adapters, still returning
mocked data (no real automation wired in until Phase 8).
