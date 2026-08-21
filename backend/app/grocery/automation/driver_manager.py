"""Appium session lifecycle management.

Every external Android app is accessed through an Appium session managed
here — Store Adapters (Phase 7) never call `appium.webdriver` directly,
only through a `DriverManager` instance (master rules #3/#5).
"""

from typing import Any, Callable

from app.grocery.automation.exceptions import AutomationConnectionError, AutomationError
from app.core.config import Settings

DriverFactory = Callable[[str, dict[str, Any]], Any]


def _default_driver_factory(server_url: str, capabilities: dict[str, Any]) -> Any:
    """Builds a real Appium session.

    Imported lazily (inside the function, not at module top) so this
    module — and every unit test exercising ``DriverManager``'s own
    logic via an injected fake factory — stays usable without the
    `appium`/`selenium` packages installed. Same pattern already used for
    the `ollama` client in ``app.core.llm.client``.
    """
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    options = UiAutomator2Options().load_capabilities(capabilities)
    return webdriver.Remote(server_url, options=options)


class DriverManager:
    """Owns a single Appium session's lifecycle: start, stop, restart.

    Composition, not inheritance — Store Adapters (Phase 7) will each
    HOLD a ``DriverManager`` instance, never subclass it, matching the
    composition-over-inheritance pattern already established for
    ``StoreAdapter`` in the Phase 0 design.
    """

    def __init__(
        self, settings: Settings, driver_factory: DriverFactory | None = None
    ) -> None:
        """
        Args:
            settings: Used for ``appium_server_url``.
            driver_factory: Optional override for how a driver is built —
                tests inject a fake factory returning a stub driver, so
                this whole class is testable without a real Appium server
                or device/emulator.
        """
        self._server_url = settings.appium_server_url
        self._driver_factory = driver_factory or _default_driver_factory
        self._driver: Any | None = None

    @property
    def driver(self) -> Any:
        """The active session's driver. Raises if no session is active."""

        if self._driver is None:
            raise AutomationError("No active Appium session. Call start() first.")
        return self._driver

    @property
    def is_active(self) -> bool:
        return self._driver is not None

    def start(self, capabilities: dict[str, Any]) -> Any:
        """Start a new Appium session with the given capabilities.

        Raises:
            AutomationError: if a session is already active — call
                ``stop()`` or ``restart()`` instead.
            AutomationConnectionError: if the session could not be
                established (server unreachable, invalid capabilities,
                device/emulator not found, etc.).
        """

        if self._driver is not None:
            raise AutomationError(
                "A session is already active. Call stop() or restart() "
                "instead of start()."
            )
        try:
            self._driver = self._driver_factory(self._server_url, capabilities)
        except AutomationError:
            raise
        except Exception as exc:
            raise AutomationConnectionError(
                f"Failed to start Appium session at {self._server_url}: {exc}"
            ) from exc
        return self._driver

    def stop(self) -> None:
        """Tear down the active session, if any. Safe to call repeatedly."""

        if self._driver is None:
            return
        try:
            self._driver.quit()
        finally:
            self._driver = None

    def restart(self, capabilities: dict[str, Any]) -> Any:
        """Session-crash recovery: best-effort teardown of a possibly
        already-dead session, then a fresh start.

        Matches Phase 0 architecture doc section 12's policy ("Driver
        Manager attempts session restart once") — this method performs
        exactly one restart attempt. Retry-count policy beyond that (how
        many times to call ``restart()`` before giving up) belongs to the
        caller, per the Tool Orchestrator's error-handling responsibility
        (Phase 7+).
        """

        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                # The session may already be dead (that's often WHY we're
                # restarting) — teardown here is best-effort, never fatal.
                pass
            finally:
                self._driver = None
        return self.start(capabilities)

    def __enter__(self) -> "DriverManager":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.stop()
        return False
