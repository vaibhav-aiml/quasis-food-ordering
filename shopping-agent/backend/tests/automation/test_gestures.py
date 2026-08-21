"""Tests for app.automation.gestures.

Requires real `selenium` installed (same as test_waits.py, since these
call through wait_for_element/wait_for_element_clickable). Not runnable
in the offline sandbox that built this phase.
"""

from app.automation.gestures import scroll_down, tap, type_text


class _FakeElement:
    def __init__(self) -> None:
        self.clicked = False
        self.cleared = False
        self.sent_keys: str | None = None

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def click(self) -> None:
        self.clicked = True

    def clear(self) -> None:
        self.cleared = True

    def send_keys(self, text: str) -> None:
        self.sent_keys = text


class _FakeDriver:
    def __init__(self, element: _FakeElement) -> None:
        self._element = element
        self.executed_scripts: list[tuple[str, dict]] = []

    def find_element(self, by: str, value: str) -> _FakeElement:
        return self._element

    def get_window_size(self) -> dict:
        return {"width": 1080, "height": 1920}

    def execute_script(self, name: str, params: dict) -> None:
        self.executed_scripts.append((name, params))


def test_tap_clicks_the_located_element() -> None:
    element = _FakeElement()
    driver = _FakeDriver(element)

    tap(driver, ("id", "btn"))

    assert element.clicked is True


def test_type_text_clears_then_sends_keys_by_default() -> None:
    element = _FakeElement()
    driver = _FakeDriver(element)

    type_text(driver, ("id", "search"), "onion")

    assert element.cleared is True
    assert element.sent_keys == "onion"


def test_type_text_skips_clear_when_disabled() -> None:
    element = _FakeElement()
    driver = _FakeDriver(element)

    type_text(driver, ("id", "search"), "onion", clear_first=False)

    assert element.cleared is False
    assert element.sent_keys == "onion"


def test_scroll_down_computes_bounds_from_actual_screen_size() -> None:
    driver = _FakeDriver(_FakeElement())

    scroll_down(driver, percent=0.5)

    assert len(driver.executed_scripts) == 1
    name, params = driver.executed_scripts[0]
    assert name == "mobile: scrollGesture"
    assert params["width"] == 1080
    assert params["height"] == 1920
    assert params["direction"] == "down"
    assert params["percent"] == 0.5


def test_scroll_down_default_percent_is_point_eight() -> None:
    driver = _FakeDriver(_FakeElement())

    scroll_down(driver)

    _, params = driver.executed_scripts[0]
    assert params["percent"] == 0.8
