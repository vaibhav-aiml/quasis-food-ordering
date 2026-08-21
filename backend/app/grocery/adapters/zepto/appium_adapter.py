"""Real, Appium-backed Zepto adapter — Phase 8 (search) + Phase 14
(cart/checkout).

Implements the SAME ``StoreAdapter`` protocol as ``ZeptoAdapter`` (Phase
7's mock) — this is exactly the payoff of building ``StoreAdapter`` as a
structural ``Protocol``: a completely different implementation, with zero
changes to the interface or to anything consuming it.

``add_to_cart``/``checkout`` now delegate to
``app.grocery.adapters._appium_order`` (Phase 14). Both return typed failure
results rather than raising — a failed cart-add or checkout is an
ordinary, recoverable business event, not a crash — in deliberate
contrast to ``search()``'s raise-based error handling below.
"""

import logging

from app.grocery.adapters._appium_order import add_product_to_cart_via_appium, checkout_via_appium
from app.grocery.adapters._appium_search import search_store_via_appium
from app.grocery.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.grocery.adapters.zepto.locators import LOCATORS
from app.grocery.automation.capabilities import build_android_capabilities
from app.grocery.automation.driver_manager import DriverManager
from app.grocery.automation.exceptions import AutomationError
from app.grocery.automation.screenshots import capture_screenshot
from app.grocery.automation.waits import DEFAULT_TIMEOUT_SECONDS
from app.core.config import Settings
from app.grocery.domain.raw_product_result import RawProductResult

STORE_ID = "zepto"

_logger = logging.getLogger("app.grocery.adapters.zepto.appium")


class ZeptoAppiumAdapter:
    """Real Appium-backed Zepto integration.

    NOTE: ``app/adapters/zepto/locators.py`` currently contains
    UNVERIFIED PLACEHOLDER locator values — see that file's docstring.
    This class's session-management and search-orchestration logic is
    complete and unit-tested (via fakes); it will not successfully
    automate the real app until those locators are replaced with values
    from a real Appium Inspector session.
    """

    def __init__(
        self, settings: Settings, driver_manager: DriverManager | None = None
    ) -> None:
        self._settings = settings
        self._driver_manager = driver_manager or DriverManager(settings)

    def get_store_id(self) -> str:
        return STORE_ID

    def is_available(self) -> bool:
        return self._driver_manager.is_active

    def _ensure_session(self) -> None:
        """Start an Appium session if one isn't already active. Idempotent."""

        if self._driver_manager.is_active:
            return
        capabilities = build_android_capabilities(
            self._settings,
            appPackage=LOCATORS.app_package,
            appActivity=LOCATORS.app_activity,
        )
        self._driver_manager.start(capabilities)

    def search(
        self, query: SearchQuery, *, timeout: float = DEFAULT_TIMEOUT_SECONDS
    ) -> list[RawProductResult]:
        self._ensure_session()
        driver = self._driver_manager.driver
        try:
            return search_store_via_appium(
                driver, STORE_ID, LOCATORS, query, timeout=timeout
            )
        except Exception as exc:
            screenshot_path = None
            try:
                screenshot_path = capture_screenshot(driver, f"{STORE_ID}_search_error")
            except Exception:
                _logger.warning(
                    "failed_to_capture_error_screenshot", extra={"store_id": STORE_ID}
                )
            raise AutomationError(
                f"Search failed for store '{STORE_ID}'"
                + (f" (screenshot: {screenshot_path})" if screenshot_path else "")
                + f": {exc}"
            ) from exc

    def add_to_cart(self, product: RawProductResult) -> CartActionResult:
        self._ensure_session()
        driver = self._driver_manager.driver
        return add_product_to_cart_via_appium(driver, STORE_ID, LOCATORS, product)

    def checkout(self) -> CheckoutState:
        self._ensure_session()
        driver = self._driver_manager.driver
        return checkout_via_appium(driver, STORE_ID, LOCATORS)
