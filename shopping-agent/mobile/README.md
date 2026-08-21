# Mobile Client (Flutter) — Placeholder

This folder is reserved for the Flutter app shown in the system architecture
(`docs/phase0_architecture.md`, §2). It is intentionally empty in Phase 1.

The phase plan builds the backend first (Phases 2–15) since it contains all the
agentic logic; the Flutter client is a thin consumer of the `/v1` API and will
be scaffolded once that API has real endpoints to call against, so we avoid
building UI against a contract that hasn't stabilized yet.
