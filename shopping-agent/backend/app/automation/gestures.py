"""Basic UI interaction primitives: tap, type, scroll.

Every function here operates only on a ``driver`` plus a locator/text —
no business logic, no product/store awareness. Master rule #3 (Appium
performs automation only) and rule #4 (never let anything upstream
directly control UI actions) both mean this file's functions are the
lowest, dumbest layer: Store Adapters (Phase 7) call these; these never
call back into adapters or business logic.
"""

from typing import Any

from app.automation.waits import (
    DEFAULT_TIMEOUT_SECONDS,
    Locator,
    wait_for_element,
    wait_for_element_clickable,
)


def tap(driver: Any, locator: Locator, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
    """Wait for an element to be clickable, then tap it."""

    element = wait_for_element_clickable(driver, locator, timeout)
    element.click()


def type_text(
    driver: Any,
    locator: Locator,
    text: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    clear_first: bool = True,
) -> None:
    """Wait for an element to be present, then type into it.

    ``clear_first=True`` (the default) clears any existing text first —
    disable it for fields where clearing would trigger unwanted
    autocomplete/search-suggestion behavior in the target app.
    """

    element = wait_for_element(driver, locator, timeout)
    cls_name = getattr(element, "get_attribute", lambda _: "")("className") or ""
    if "EditText" not in str(cls_name) and hasattr(element, "click"):
        try:
            element.click()
            edit_elements = driver.find_elements("xpath", "//android.widget.EditText")
            if edit_elements:
                element = edit_elements[0]
        except Exception:
            pass

    if clear_first:
        try:
            element.clear()
        except Exception:
            pass
    try:
        element.send_keys(text)
    except Exception:
        active = getattr(driver, "switch_to", None)
        if active and hasattr(active, "active_element"):
            active.active_element.send_keys(text)
        else:
            raise


def scroll_down(driver: Any, percent: float = 0.8) -> None:
    """Scroll down within the full visible screen area.

    Uses Appium's UiAutomator2 ``mobile: scrollGesture`` command
    (parameters verified against current Appium documentation before
    writing this). The scroll bounding box is computed from the device's
    actual screen size via ``get_window_size()`` rather than hardcoded
    pixel coordinates — makes this portable across devices/emulators with
    different resolutions.
    """

    size = driver.get_window_size()
    driver.execute_script(
        "mobile: scrollGesture",
        {
            "left": 0,
            "top": 0,
            "width": size["width"],
            "height": size["height"],
            "direction": "down",
            "percent": percent,
        },
    )
