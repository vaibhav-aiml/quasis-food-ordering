"""Tests for app.grocery.automation.waits.

These exercise the actual Selenium `WebDriverWait` polling loop against a
fake driver/element -- not a fully mocked wait mechanism -- so they
require the real `selenium` package (a project dependency per
requirements.txt). Not runnable in the offline sandbox that built this
phase; see Phase 6 docs for what WAS verified there.
"""

import pytest
from selenium.common.exceptions import NoSuchElementException

from app.grocery.automation.exceptions import AutomationTimeoutError
from app.grocery.automation.waits import wait_for_element, wait_for_element_clickable


class _FakeElement:
    def __init__(self, displayed: bool = True, enabled: bool = True) -> None:
        self._displayed = displayed
        self._enabled = enabled

    def is_displayed(self) -> bool:
        return self._displayed

    def is_enabled(self) -> bool:
        return self._enabled


class _FakeDriver:
    def __init__(self, element: _FakeElement | None = None) -> None:
        self._element = element

    def find_element(self, by: str, value: str):
        if self._element is None:
            raise NoSuchElementException(f"no element for ({by}, {value})")
        return self._element


def test_wait_for_element_returns_element_when_present() -> None:
    element = _FakeElement()
    driver = _FakeDriver(element=element)

    result = wait_for_element(driver, ("id", "some_id"), timeout=1.0)

    assert result is element


def test_wait_for_element_raises_automation_timeout_error_when_missing() -> None:
    driver = _FakeDriver(element=None)

    with pytest.raises(AutomationTimeoutError):
        wait_for_element(driver, ("id", "missing"), timeout=0.3)


def test_wait_for_element_clickable_returns_element_when_visible_and_enabled() -> None:
    element = _FakeElement(displayed=True, enabled=True)
    driver = _FakeDriver(element=element)

    result = wait_for_element_clickable(driver, ("id", "btn"), timeout=1.0)

    assert result is element


def test_wait_for_element_clickable_times_out_when_not_enabled() -> None:
    element = _FakeElement(displayed=True, enabled=False)
    driver = _FakeDriver(element=element)

    with pytest.raises(AutomationTimeoutError):
        wait_for_element_clickable(driver, ("id", "btn"), timeout=0.3)


def test_wait_for_element_clickable_times_out_when_not_displayed() -> None:
    element = _FakeElement(displayed=False, enabled=True)
    driver = _FakeDriver(element=element)

    with pytest.raises(AutomationTimeoutError):
        wait_for_element_clickable(driver, ("id", "btn"), timeout=0.3)
