"""Explicit wait strategies over Appium/Selenium's ``WebDriverWait``.

Deliberately never uses ``time.sleep()`` — polling explicit waits handle
the variable, network-dependent load times of quick-commerce apps far
more reliably (Phase 0 architecture doc, section 7). Imports of
`selenium`/`appium` submodules are deferred to call time, matching the
pattern already used for the `ollama` client in `app.core.llm.client` —
keeps this module (and the logic built on it) testable via a fake driver
without those packages needing to be installed for that testing.
"""

from typing import Any

from app.grocery.automation.exceptions import AutomationTimeoutError

Locator = tuple[str, str]

DEFAULT_TIMEOUT_SECONDS = 10.0


def wait_for_element(
    driver: Any, locator: Locator, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> Any:
    """Wait until an element matching ``locator`` is present.

    "Present" means found in the element tree — not necessarily visible
    or interactable. Use ``wait_for_element_clickable`` when the caller
    is about to tap/type into it.
    """

    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except Exception as exc:
        raise AutomationTimeoutError(
            f"Timed out after {timeout}s waiting for element {locator!r} to be present"
        ) from exc


def wait_for_element_clickable(
    driver: Any, locator: Locator, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> Any:
    """Wait until an element matching ``locator`` is present, visible,
    and enabled — i.e. safe to tap.
    """

    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
    except Exception as exc:
        raise AutomationTimeoutError(
            f"Timed out after {timeout}s waiting for element {locator!r} to be clickable"
        ) from exc
