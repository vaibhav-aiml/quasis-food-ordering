"""Tests for app.grocery.automation.driver_manager.DriverManager.

Uses a hand-written fake driver factory -- no real Appium server or
device/emulator needed, and no mocking library. Same pattern already
proven for FakeLLMClient (Phase 3) and StoreAdapter-style fakes
throughout this project.
"""

import pytest

from app.grocery.automation.driver_manager import DriverManager
from app.grocery.automation.exceptions import AutomationConnectionError, AutomationError
from app.core.config import Settings


class _FakeDriver:
    def __init__(self) -> None:
        self.quit_called = False

    def quit(self) -> None:
        self.quit_called = True


class _DeadDriver:
    """A driver whose .quit() raises -- simulates a session that already
    crashed, to test restart()'s best-effort teardown.
    """

    def quit(self) -> None:
        raise RuntimeError("session already terminated")


def _settings() -> Settings:
    return Settings(_env_file=None, appium_server_url="http://fake-appium:4723")  # type: ignore[call-arg]


def test_start_creates_session_via_injected_factory() -> None:
    created: dict = {}

    def factory(server_url: str, caps: dict) -> _FakeDriver:
        created["server_url"] = server_url
        created["caps"] = caps
        return _FakeDriver()

    manager = DriverManager(_settings(), driver_factory=factory)
    driver = manager.start({"platformName": "Android"})

    assert manager.is_active is True
    assert driver is manager.driver
    assert created["server_url"] == "http://fake-appium:4723"
    assert created["caps"] == {"platformName": "Android"}


def test_start_twice_without_stop_raises_automation_error() -> None:
    manager = DriverManager(_settings(), driver_factory=lambda url, caps: _FakeDriver())
    manager.start({})

    with pytest.raises(AutomationError):
        manager.start({})


def test_driver_property_raises_before_start() -> None:
    manager = DriverManager(_settings(), driver_factory=lambda url, caps: _FakeDriver())

    with pytest.raises(AutomationError):
        _ = manager.driver


def test_is_active_false_before_start() -> None:
    manager = DriverManager(_settings(), driver_factory=lambda url, caps: _FakeDriver())
    assert manager.is_active is False


def test_stop_quits_driver_and_clears_state() -> None:
    fake = _FakeDriver()
    manager = DriverManager(_settings(), driver_factory=lambda url, caps: fake)
    manager.start({})

    manager.stop()

    assert fake.quit_called is True
    assert manager.is_active is False


def test_stop_when_not_started_is_a_no_op() -> None:
    manager = DriverManager(_settings(), driver_factory=lambda url, caps: _FakeDriver())
    manager.stop()  # must not raise
    assert manager.is_active is False


def test_restart_tears_down_old_session_and_starts_new_one() -> None:
    old = _FakeDriver()
    new = _FakeDriver()
    drivers = [old, new]

    manager = DriverManager(_settings(), driver_factory=lambda url, caps: drivers.pop(0))
    manager.start({})

    result = manager.restart({})

    assert old.quit_called is True
    assert result is new
    assert manager.driver is new


def test_restart_survives_a_dead_session_quit_raising() -> None:
    new = _FakeDriver()
    drivers = [_DeadDriver(), new]

    manager = DriverManager(_settings(), driver_factory=lambda url, caps: drivers.pop(0))
    manager.start({})

    result = manager.restart({})  # must not raise despite _DeadDriver.quit() raising

    assert result is new
    assert manager.driver is new


def test_start_wraps_factory_exception_in_automation_connection_error() -> None:
    def failing_factory(url: str, caps: dict) -> None:
        raise ConnectionRefusedError("no appium server listening")

    manager = DriverManager(_settings(), driver_factory=failing_factory)

    with pytest.raises(AutomationConnectionError):
        manager.start({})


def test_context_manager_stops_session_on_exit() -> None:
    fake = _FakeDriver()
    with DriverManager(_settings(), driver_factory=lambda url, caps: fake) as manager:
        manager.start({})
        assert manager.is_active is True

    assert fake.quit_called is True
