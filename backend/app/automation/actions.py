"""Core atomic UI automation actions using uiautomator2."""

import logging
import os
import time
from typing import Any
from app.automation.config import get_automation_config
from app.automation.exceptions import ActionTimeoutError, ElementNotFoundError
from app.automation.locators import SWIGGY_LOCATORS, get_locator_strategies

logger = logging.getLogger("app.automation.actions")


def _resolve_strategies(locator: str | dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize input locator into a list of strategy dictionaries."""
    if isinstance(locator, str):
        if locator in SWIGGY_LOCATORS:
            return get_locator_strategies(locator)
        # If it's a raw string, treat as text match
        return [{"text": locator}, {"textContains": locator}, {"descriptionContains": locator}]
    if isinstance(locator, dict):
        return [locator]
    if isinstance(locator, list):
        return locator
    raise ValueError(f"Unsupported locator format: {type(locator)}")


def _build_u2_selector(d: Any, strategy: dict[str, Any]) -> Any:
    """Construct a uiautomator2 UIObject selector from a strategy dict."""
    if "xpath" in strategy and hasattr(d, "xpath"):
        return d.xpath(strategy["xpath"])
    return d(**strategy)


def find_element(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float | None = None,
) -> Any | None:
    """Find a UI element using a cascade of locator strategies.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Key string, single selector dict, or list of selector dicts.
        timeout: Maximum wait time in seconds. Defaults to config.default_timeout.

    Returns:
        uiautomator2 UIObject/XPath object if found, or None.
    """
    config = get_automation_config()
    wait_time = timeout if timeout is not None else config.default_timeout
    strategies = _resolve_strategies(locator)
    start_time = time.time()
    per_strategy_wait = max(0.5, wait_time / len(strategies))

    for strategy in strategies:
        try:
            elem = _build_u2_selector(d, strategy)
            exists_attr = getattr(elem, "exists", None)
            if exists_attr is not None:
                if callable(exists_attr):
                    exists = bool(exists_attr(timeout=per_strategy_wait))
                else:
                    exists = bool(exists_attr)

                if exists:
                    logger.debug("Found element using strategy: %s", strategy)
                    return elem
        except Exception as e:
            logger.debug("Strategy %s failed: %s", strategy, e)

        if time.time() - start_time >= wait_time:
            break

    return None


def wait_for_element(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float | None = None,
    poll_interval: float | None = None,
) -> Any:
    """Wait until an element appears on screen, or raise ElementNotFoundError.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Key string, single selector dict, or list of selector dicts.
        timeout: Maximum wait time in seconds.
        poll_interval: Polling frequency.

    Returns:
        uiautomator2 UIObject / XPath object.

    Raises:
        ElementNotFoundError: If element does not appear within timeout.
    """
    config = get_automation_config()
    wait_time = timeout if timeout is not None else config.default_timeout
    poll = poll_interval if poll_interval is not None else config.poll_interval
    start_time = time.time()

    while time.time() - start_time < wait_time:
        elem = find_element(d, locator, timeout=poll)
        if elem is not None:
            return elem
        time.sleep(poll)

    raise ElementNotFoundError(
        f"Element matching locator '{locator}' was not found within {wait_time}s timeout."
    )


def is_element_present(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float | None = None,
) -> bool:
    """Check whether an element is currently visible on screen.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator.
        timeout: Short lookup timeout. Defaults to config.short_timeout.

    Returns:
        True if present, False otherwise.
    """
    config = get_automation_config()
    lookup_timeout = timeout if timeout is not None else config.short_timeout
    elem = find_element(d, locator, timeout=lookup_timeout)
    return elem is not None


def click_element(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float | None = None,
    retries: int | None = None,
    delay_after: float | None = None,
) -> bool:
    """Click an element with automatic retries and fallback mechanisms.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator.
        timeout: Timeout to find the element.
        retries: Number of retry attempts.
        delay_after: Delay in seconds after click.

    Returns:
        True if click succeeded, False otherwise.
    """
    config = get_automation_config()
    max_attempts = retries if retries is not None else config.max_retries
    pause_after = delay_after if delay_after is not None else config.action_delay

    for attempt in range(1, max_attempts + 1):
        try:
            elem = wait_for_element(d, locator, timeout=timeout)
            if elem is not None:
                # Attempt direct click
                if hasattr(elem, "click"):
                    elem.click()
                    logger.debug("Clicked element successfully on attempt %s", attempt)
                    if pause_after > 0:
                        time.sleep(pause_after)
                    return True
        except Exception as e:
            logger.warning("Click attempt %s failed for locator '%s': %s", attempt, locator, e)
            time.sleep(0.5 * attempt)

    # Final attempt: coordinate tap fallback if bounds are available
    try:
        elem = find_element(d, locator, timeout=1.0)
        if elem and hasattr(elem, "bounds"):
            bounds = elem.bounds() if callable(getattr(elem, "bounds", None)) else elem.bounds
            center_x = (bounds[0] + bounds[2]) // 2
            center_y = (bounds[1] + bounds[3]) // 2
            logger.info("Performing fallback coordinate tap at (%s, %s)", center_x, center_y)
            d.click(center_x, center_y)
            if pause_after > 0:
                time.sleep(pause_after)
            return True
    except Exception as e:
        logger.error("Coordinate fallback click failed: %s", e)

    return False


def set_text(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    text: str,
    clear: bool = True,
    press_enter: bool = False,
) -> bool:
    """Type text into an input field.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator for the input element.
        text: String text to enter.
        clear: Whether to clear existing content before typing.
        press_enter: Whether to simulate pressing the Enter key after typing.

    Returns:
        True if text was entered successfully, False otherwise.
    """
    config = get_automation_config()
    try:
        elem = wait_for_element(d, locator, timeout=config.default_timeout)
        if elem is None:
            return False

        # Click element first to ensure it has focus, then wait for keyboard/input
        try:
            if hasattr(elem, "click"):
                elem.click()
                time.sleep(0.5)
        except Exception:
            pass

        if clear and hasattr(elem, "clear_text"):
            try:
                elem.clear_text()
            except Exception:
                pass

        text_set = False
        # Strategy 1: Direct set_text
        if hasattr(elem, "set_text"):
            try:
                elem.set_text(text)
                text_set = True
            except Exception as e:
                logger.debug("set_text failed: %s", e)

        # Strategy 2: send_keys on element
        if not text_set and hasattr(elem, "send_keys"):
            try:
                elem.send_keys(text)
                text_set = True
            except Exception as e:
                logger.debug("elem.send_keys failed: %s", e)

        # Strategy 3: Device-level send_keys (uses fastinput_ime)
        if not text_set:
            try:
                click_element(d, locator)
                time.sleep(0.3)
                d.send_keys(text)
                text_set = True
            except Exception as e:
                logger.debug("d.send_keys fallback failed: %s", e)

        # Strategy 4: Shell input text
        if not text_set:
            try:
                d.shell(f"input text '{text}'")
                text_set = True
            except Exception as e:
                logger.debug("shell input text failed: %s", e)

        if not text_set:
            logger.error("All text entry strategies failed for '%s'.", text)
            return False

        logger.debug("Entered text '%s' into input field.", text)

        if press_enter:
            time.sleep(0.3)
            # Try Enter key first, then Search key (keycode 84)
            press_key(d, "enter")
            try:
                if hasattr(d, "shell"):
                    d.shell("input keyevent 84")
            except Exception:
                pass

        time.sleep(config.action_delay)
        return True
    except Exception as e:
        logger.error("Failed to set text '%s': %s", text, e)
        return False


def scroll_to_element(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    max_swipes: int | None = None,
    direction: str = "down",
    swipe_distance: float | None = None,
) -> Any | None:
    """Scroll/swipe the screen until target element becomes visible.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator.
        max_swipes: Maximum number of scroll attempts.
        direction: 'down' (scroll down / swipe up) or 'up' (scroll up / swipe down).
        swipe_distance: Fraction of screen height to swipe.

    Returns:
        Found UIObject/XPath or None if not found after max scrolls.
    """
    config = get_automation_config()
    swipes = max_swipes if max_swipes is not None else config.max_scroll_attempts
    dist = swipe_distance if swipe_distance is not None else config.scroll_swipe_distance

    # First check if already visible
    elem = find_element(d, locator, timeout=1.0)
    if elem is not None:
        return elem

    for i in range(1, swipes + 1):
        logger.debug("Swiping %s (attempt %s/%s) to find element...", direction, i, swipes)
        swipe(d, direction=direction, distance=dist)
        time.sleep(0.6)

        elem = find_element(d, locator, timeout=1.5)
        if elem is not None:
            logger.debug("Found element after %s scroll(s)", i)
            return elem

    logger.warning("Element '%s' not found after %s scrolls.", locator, swipes)
    return None


def swipe(
    d: Any,
    direction: str = "down",
    distance: float = 0.4,
    duration: float = 0.25,
) -> None:
    """Perform a directional touch swipe gesture.

    Args:
        d: Connected uiautomator2 Device instance.
        direction: 'down' (scroll down), 'up' (scroll up), 'left', or 'right'.
        distance: Relative swipe distance across screen dimensions.
        duration: Swipe gesture duration in seconds.
    """
    try:
        if hasattr(d, "swipe_ext"):
            # uiautomator2 high-level swipe
            d.swipe_ext(direction, scale=distance)
            return
    except Exception:
        pass

    # Coordinate-based fallback
    try:
        window_size = d.window_size() if callable(getattr(d, "window_size", None)) else (1080, 2400)
        width, height = window_size[0], window_size[1]
        mid_x = width // 2
        mid_y = height // 2
        offset_y = int(height * distance / 2)
        offset_x = int(width * distance / 2)

        if direction == "down":
            # Swipe upwards to scroll down
            d.swipe(mid_x, mid_y + offset_y, mid_x, mid_y - offset_y, duration)
        elif direction == "up":
            # Swipe downwards to scroll up
            d.swipe(mid_x, mid_y - offset_y, mid_x, mid_y + offset_y, duration)
        elif direction == "left":
            d.swipe(mid_x + offset_x, mid_y, mid_x - offset_x, mid_y, duration)
        elif direction == "right":
            d.swipe(mid_x - offset_x, mid_y, mid_x + offset_x, mid_y, duration)
    except Exception as e:
        logger.error("Failed to execute swipe '%s': %s", direction, e)


def get_element_text(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float = 2.0,
) -> str | None:
    """Extract and return text content from a UI element.

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator.
        timeout: Wait timeout.

    Returns:
        String text if found, or None.
    """
    elem = find_element(d, locator, timeout=timeout)
    if elem is None:
        return None

    try:
        if hasattr(elem, "get_text") and callable(elem.get_text):
            return elem.get_text()
        if hasattr(elem, "text"):
            return elem.text
    except Exception:
        pass
    return None


def get_all_matching_elements(
    d: Any,
    locator: str | dict[str, Any] | list[dict[str, Any]],
    timeout: float = 3.0,
    max_results: int = 10,
) -> list[Any]:
    """Find ALL UI elements matching a locator (not just the first one).

    Args:
        d: Connected uiautomator2 Device instance.
        locator: Target locator.
        timeout: Wait timeout per strategy.
        max_results: Maximum number of results to return.

    Returns:
        List of matching UIObject elements.
    """
    strategies = _resolve_strategies(locator)
    results: list[Any] = []
    seen_bounds: set[tuple] = set()

    for strategy in strategies:
        try:
            if "xpath" in strategy and hasattr(d, "xpath"):
                xpath_results = d.xpath(strategy["xpath"]).all()
                for elem in xpath_results:
                    try:
                        bounds = elem.bounds if hasattr(elem, "bounds") else None
                        bounds_key = tuple(bounds) if bounds else id(elem)
                        if bounds_key not in seen_bounds:
                            seen_bounds.add(bounds_key)
                            results.append(elem)
                    except Exception:
                        results.append(elem)
            else:
                selector = d(**strategy)
                if hasattr(selector, "count"):
                    count = selector.count
                    if callable(count):
                        count = count()
                    for i in range(min(count, max_results)):
                        try:
                            child = selector[i] if hasattr(selector, "__getitem__") else selector
                            results.append(child)
                        except Exception:
                            pass
                elif hasattr(selector, "exists"):
                    exists = selector.exists
                    if callable(exists):
                        exists = exists(timeout=1.0)
                    if exists:
                        results.append(selector)
        except Exception as e:
            logger.debug("get_all_matching_elements strategy %s failed: %s", strategy, e)

        if len(results) >= max_results:
            break

    return results[:max_results]


def press_key(d: Any, key: str) -> None:
    """Simulate a hardware or system key press ('back', 'home', 'enter', 'recent')."""
    try:
        if hasattr(d, "press"):
            d.press(key)
        else:
            key_codes = {"back": 4, "home": 3, "enter": 66}
            code = key_codes.get(key.lower(), 4)
            if hasattr(d, "shell"):
                d.shell(f"input keyevent {code}")
    except Exception as e:
        logger.warning("Failed to press key '%s': %s", key, e)


def take_screenshot(d: Any, file_path: str | None = None) -> str:
    """Capture a screenshot of the current Android display and save to disk.

    Args:
        d: Connected uiautomator2 Device instance.
        file_path: Optional explicit output file path.

    Returns:
        Saved screenshot file path.
    """
    config = get_automation_config()
    os.makedirs(config.screenshots_dir, exist_ok=True)

    target_path = file_path or os.path.join(
        config.screenshots_dir, f"screenshot_{int(time.time() * 1000)}.png"
    )

    try:
        if hasattr(d, "screenshot"):
            d.screenshot(target_path)
            logger.info("Screenshot saved to: %s", target_path)
            return target_path
    except Exception as e:
        logger.error("Failed to take screenshot: %s", e)

    return ""
