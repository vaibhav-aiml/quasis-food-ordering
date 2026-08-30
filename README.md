# 🍔 Quasis — AI Agent for Autonomous Food Ordering

Turn a natural-language craving into a placed order. Quasis is an agentic system that takes a spoken or typed intent — *"get me a cheap iced latte from Third Wave Coffee"* — and carries it through AI-powered understanding, deterministic ranking, and real execution on the Swiggy food-delivery app, with a human always in the loop before anything is paid for.

The project ships two independent execution engines built for different tradeoffs between speed and autonomy, plus a shared quick-commerce grocery agent for Zepto/Blinkit/Instamart. All three live in this monorepo.

---

## 📖 Table of Contents

- [Why This Exists](#-why-this-exists)
- [Architecture: Two Execution Engines](#-architecture-two-execution-engines)
  - [1. Deep-Link Handoff Pipeline (TypeScript)](#1-deep-link-handoff-pipeline-typescript)
  - [2. On-Device UI Automation Engine (Python)](#2-on-device-ui-automation-engine-python)
  - [3. Quick-Commerce Grocery Agent (Python + LangGraph)](#3-quick-commerce-grocery-agent-python--langgraph)
- [Feature Highlights](#-feature-highlights)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Contributors](#-contributors)
- [License](#-license)

---

## 🧠 Why This Exists

Ordering food through an app still means: open app → search → scroll through menus → pick a restaurant → filter by price/diet → add to cart → checkout. Quasis compresses that into one sentence, spoken or typed, and lets an agent do the rest — while keeping a human approval step before any money moves.

The system is deliberately built around two different philosophies of "autonomous", because they serve different real-world constraints:

| Feature | ⚡ Deep-Link Handoff Engine | 🤖 On-Device UI Automation Engine |
| :--- | :--- | :--- |
| **Where it lives** | `services/backend` + `apps/mobile` | `backend/app/automation` |
| **How it acts** | Generates a native `swiggy://` deep link staged with the right restaurant/item, opens it, human taps confirm | Drives the real Swiggy Android UI via ADB — searches, selects, customizes, adds to cart |
| **Device requirement** | None — works on iOS, Android, or Web | Android device/emulator with USB debugging enabled |
| **Speed** | Near-instant (~50ms to generate the link) | Slower — real UI navigation, subject to app-update drift |
| **Resilience** | Immune to UI/layout changes in the Swiggy app | Sensitive to Swiggy UI updates, popups, and OS-level dialogs |
| **Stops before payment** | Always — user completes checkout manually in the real app | Always — hard safety invariant (`stop_before_payment`) enforced in the domain model |

Both are real, tested, and merged into `main` today. See [Roadmap](#-roadmap) for how they're intended to converge.

---

## 🏗️ Architecture: Two Execution Engines

### 1. Deep-Link Handoff Pipeline (TypeScript)

```text
Voice / Text Prompt
       │
       ▼
┌───────────────────┐      Groq LLM (gpt-oss-20b)
│ Intent Extractor  │◄──── or deterministic regex/NLP fallback
└───────────────────┘      (budget, restaurant, dietary prefs)
       │
       ▼
┌───────────────────┐
│   Restaurant &    │      Token-overlap + rating-weighted ranking
│    Menu Search    │      over catalog / Groq-assisted universal search
└───────────────────┘
       │
       ▼
┌───────────────────┐
│  Human Approval   │      Live pipeline trace streamed via SSE/WebSocket
│   Card (mobile)   │ ───► user approves or rejects
└───────────────────┘
       │
       ▼
swiggy://explore?query=... (+ web fallback URL)
```

- **Real-time execution trace**: Every pipeline stage (`PARSING_INTENT` → `SEARCHING_RESTAURANTS` → `FILTERING_MENU` → `AWAITING_APPROVAL` → `COMPLETED`) streams to the mobile client over WebSocket, with SSE and polling fallbacks.
- **Voice ordering**: On-device audio capture (web MediaRecorder / native `expo-audio`) transcribed via Groq Whisper (`whisper-large-v3`), tuned with a domain-specific prompt for Indian food/restaurant vocabulary.
- **Persistent order history & favorites**: Orders are saved locally (cross-platform storage — `AsyncStorage` on native, `localStorage` on web), with instant re-dispatch or full pipeline re-run from history.
- **Abuse protection**: Sliding-window rate limiting (20 req/min/IP) on the paid Whisper transcription endpoint, with automatic stale-entry eviction.

---

### 2. On-Device UI Automation Engine (Python)

```text
FoodOrderIntent (Pydantic, multi-item, confidence-scored)
       │
       ▼
OrderPlan ──► [OrderStep, OrderStep, ...]
       │
       ▼
┌────────────────────────────────────────────┐
│         uiautomator2 Orchestrator          │
│  ├─ device_manager (ADB connection)        │
│  ├─ locators (multi-strategy: ID /         │
│  │   text / a11y / XPath /                 │
│  │   coordinate fallback)                  │
│  ├─ actions (tap, type, scroll)            │
│  ├─ popup_handler (dismiss system/promo    │
│  │   dialogs mid-flow)                     │
│  └─ safety_guard (halts before payment)    │
└────────────────────────────────────────────┘
       │
       ▼
FoodExecutionState ──► READY_FOR_PAYMENT (human takes over)
```

- **Function-based automation core** (no stateful class hierarchies) operating directly on `uiautomator2.Device` instances.
- **Multi-strategy element location with automatic fallback**: resource ID → text match → accessibility description → XPath → coordinate tap.
- **Safety-first design**: `stop_before_payment` is a hard invariant on every generated plan — the automation engine is architecturally incapable of completing a purchase without a human handoff.

---

### 3. Quick-Commerce Grocery Agent (Python + LangGraph)

A parallel, fully-tested agent (`backend/app/grocery`) that turns grocery intents (*"making biryani, need onions and curd, cheapest under 20 min"*) into ranked, verified recommendations across Zepto/Blinkit/Instamart using LangGraph-orchestrated LLM reasoning + deterministic Python scoring. See [`docs/grocery/phase0_architecture.md`](docs/grocery/phase0_architecture.md) for the full design.

---

## ✨ Feature Highlights

- 🎙️ **Voice-to-order** — speak your craving, Groq Whisper transcribes it, the agent takes it from there
- 🧾 **Persistent order history & favorites** with one-tap re-order (instant dispatch or full re-run)
- 🔁 **Live agent trace** — watch intent parsing, search, and ranking happen in real time on-device
- ✅ **Human-in-the-loop by design** — no order is ever placed without explicit approval
- 🛡️ **Rate-limited, abuse-resistant API** for all LLM-backed endpoints
- 📱 **Cross-platform mobile client** (iOS / Android / Web) built with Expo + React Native
- 🤖 **Optional full autonomy** via on-device Android automation for users who pair a device over ADB
- 🧪 **392 automated tests** across both stacks, all passing on `main`

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Mobile app** | React Native 0.78, Expo SDK 54, TypeScript |
| **Deep-link backend** | Node.js, Express, WebSocket, Zod |
| **AI — intent & search** | Groq (`gpt-oss-20b`) with deterministic regex/NLP fallback |
| **AI — voice** | Groq Whisper (`whisper-large-v3`) |
| **Automation engine** | Python 3.12+, `uiautomator2`, ADB, Pydantic v2 |
| **Grocery agent** | FastAPI, LangGraph, LangChain-core, Ollama |
| **Testing** | Vitest (TypeScript), Pytest + pytest-asyncio (Python) |
| **CI/CD** | GitHub Actions (standalone Android APK build via Expo prebuild) |

---

## 📂 Repository Structure

```text
quasis-food-ordering/
├── apps/mobile/             # Expo/React Native client (voice, history, live trace UI)
├── services/backend/        # TypeScript deep-link pipeline (Express + WebSocket)
│   ├── src/agent/           # intent extraction, Whisper transcription, orchestrator
│   ├── src/tools/swiggy/    # catalog, ranking, deep-link generation
│   └── tests/               # Vitest suite (pipeline, e2e, whisper)
├── backend/
│   ├── app/automation/      # Python uiautomator2 on-device automation engine
│   ├── app/food_ordering/   # Pydantic domain models (intent, plan, execution)
│   ├── app/grocery/         # LangGraph quick-commerce agent (Zepto/Blinkit/Instamart)
│   └── tests/               # Pytest suite (380 tests across automation + grocery)
├── docs/grocery/            # Phased architecture docs for the grocery agent
└── .github/workflows/       # CI: standalone Android APK build
```

---

## 🚀 Getting Started

### Deep-Link Engine (TypeScript backend + mobile app)

```bash
# 1. Backend
cd services/backend
npm install
cp .env.example .env       # add your GROQ_API_KEY (optional — falls back to rule-based parsing)
npm run dev                # starts on http://localhost:3001

# 2. Mobile app (in a new terminal)
cd apps/mobile
npm install
npm start                  # opens Expo dev tools — scan QR with Expo Go, or press `w` for web
```

### On-Device Automation Engine (Python)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload  # starts on http://localhost:8000
```

> **Note:** Real UI automation requires an Android device or emulator connected with `adb devices` showing it as authorized.

---

## 🧪 Testing

All tests are green on `main`:

```bash
# TypeScript (12/12 passing)
cd services/backend && npm test

# Python (380/380 passing — 346 grocery/core + 34 automation)
cd backend && source .venv/bin/activate && pytest
```

---

## 🗺️ Roadmap

The two execution engines currently operate independently. Planned convergence work:

1. **Dual dispatch modes in the mobile UI** — a default *"⚡ Instant Link"* mode and an opt-in *"🤖 Autonomous Bot"* mode for users with a paired Android device.
2. **Unified fallback strategy** — attempt deep-link dispatch first; automatically delegate to on-device automation for orders with complex customizations (e.g. multi-step modifier sheets) that can't be expressed via URL schema.
3. **Shared intent contract** — anchor on the richer Python `FoodOrderIntent` (multi-item, confidence-scored, clarification-aware) as the canonical schema, and generate matching Zod/TypeScript types so both engines speak the same domain language. *This is a proposed milestone, not yet implemented, and will also require updating the TypeScript pipeline logic to handle multi-item and clarification flows, not just the type definitions.*

---

## 👥 Contributors

Built and maintained by [Vaibhav Badaya](https://github.com/vaibhav-aiml) (deep-link pipeline, voice ordering, mobile app) in collaboration with Aman (on-device automation engine, quick-commerce grocery agent).

---

## 📄 License

No license file is currently published in this repository. All rights reserved by the authors unless a license is added.
