# Python + uiautomator2 Food Ordering Automation Module

This module provides a reliable, function-based Android UI automation system for food ordering (Swiggy) and quick-commerce workflows. It replaces the legacy Kotlin AccessibilityService architecture with high-speed UIAutomator instrumentation over ADB.

---

## Architecture Overview

```
backend/app/automation/
├── __init__.py               # Package exports
├── config.py                 # Timeouts, retry counts, package names, device configs
├── exceptions.py             # Custom exception hierarchy
├── device_manager.py         # Device connection, ADB daemon, device info
├── locators.py               # Multi-strategy UI element locators
├── actions.py                # Core atomic UI primitives (click, type, scroll, wait, swipe)
├── popup_handler.py          # Dynamic overlay/popup detection and dismissal
├── safety_guard.py           # Payment boundary detection and safety halts
├── swiggy_flows.py           # End-to-end Swiggy user journeys
└── orchestrator.py           # Execution engine & order state machine
```

---

## Key Features

1. **Pure Function-Based Paradigm:**
   No complex stateful class hierarchies. Functions operate cleanly on `u2.Device` instances, preventing concurrency issues and OOP lifecycle bugs.

2. **Multi-Strategy Locators:**
   Every UI element definition in `locators.py` includes a prioritized fallback chain:
   - Resource ID match
   - Text / partial text (`textMatches`, `textContains`)
   - Accessibility content description
   - XPath / Relative hierarchy
   - Screen coordinate tap fallback

3. **Dynamic Popup Suppression:**
   `popup_handler.py` automatically sweeps and dismisses system permission dialogs (location, notifications), promotional bottom sheets, update alerts, and delivery address confirmations.

4. **Strict Safety Boundary:**
   `safety_guard.py` inspects screens and interactive buttons before any click. If a payment screen ("Pay ₹", UPI PIN, CVV, Card Details) is reached, execution strictly halts with `STOPPED_AT_PAYMENT` for human takeover.

---

## Prerequisites & Setup

### 1. Python Dependencies
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### 2. Device Connectivity
Connect an Android device with USB debugging enabled, or start an Android emulator:
```bash
# Check connected devices
adb devices
```

### 3. UI Inspection (Optional)
To inspect Swiggy UI hierarchy and test locators interactively:
```bash
python -m weditor
```

---

## Usage Examples

### Quick Start: Execute an Order Plan
```python
from app.automation.orchestrator import execute_order_plan
from app.food_ordering.domain.plan import OrderPlan, OrderStep, ExecutionStepType

plan = OrderPlan(
    plan_id="plan_123",
    restaurant_name="Domino's Pizza",
    steps=[
        OrderStep(step_id=1, step_type=ExecutionStepType.LAUNCH_APP, expected_screen="home"),
        OrderStep(step_id=2, step_type=ExecutionStepType.SEARCH_RESTAURANT, target_value="Domino's Pizza", expected_screen="search_results"),
        OrderStep(step_id=3, step_type=ExecutionStepType.SELECT_RESTAURANT, target_value="Domino's Pizza", expected_screen="restaurant_menu"),
        OrderStep(step_id=4, step_type=ExecutionStepType.ADD_TO_CART, target_value="Margherita Pizza", parameters={"quantity": 1}, expected_screen="restaurant_menu"),
        OrderStep(step_id=5, step_type=ExecutionStepType.VIEW_CART, expected_screen="cart"),
        OrderStep(step_id=6, step_type=ExecutionStepType.STOP_FOR_PAYMENT, expected_screen="payment"),
    ]
)

result = execute_order_plan(plan)
print(result["status"])  # "READY_FOR_PAYMENT"
print(result["result"])  # "STOPPED_AT_PAYMENT"
```

---

## Running Automated Tests

Run the dedicated test suite:
```bash
pytest tests/automation/
```
