# Android Kotlin AccessibilityService (DEPRECATED)

> [!WARNING]
> **DEPRECATION NOTICE:**
> The Kotlin AccessibilityService module in this directory is **deprecated** following architectural migration to the **Python + uiautomator2** automation engine (located in `backend/app/automation/`).
>
> This codebase is retained temporarily as a reference/backup during Phase 1-4 and will be removed in Phase 5 upon completion of real-device validation.

## Why this approach was deprecated
- Frequent AccessibilityNode tree synchronization failures on dynamic Swiggy UI updates
- High latency and reliability issues when dispatching multi-touch gestures to cart buttons
- Difficulty debugging Android OS accessibility events in production without interactive repls
- Heavy maintenance burden on the team compared to pure Python automation
