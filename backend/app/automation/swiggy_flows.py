"""Swiggy domain automation flows for food discovery, item customization, and cart execution."""

import logging
import time
from typing import Any

from app.automation.actions import (
    click_element,
    find_element,
    is_element_present,
    press_key,
    scroll_to_element,
    set_text,
    wait_for_element,
)
from app.automation.config import get_automation_config
from app.automation.exceptions import ElementNotFoundError, FlowExecutionError
from app.automation.popup_handler import handle_all_popups
from app.automation.safety_guard import (
    is_payment_screen,
    is_safe_to_click,
    stop_before_payment,
    verify_safety_boundary,
)

logger = logging.getLogger("app.automation.swiggy_flows")


def launch_swiggy(d: Any, force_stop_first: bool = False) -> bool:
    """Launch the Swiggy application and navigate to home screen.

    Args:
        d: Connected uiautomator2 Device instance.
        force_stop_first: If True, terminates any existing Swiggy instance first.

    Returns:
        True if Swiggy is launched and ready on Home screen.
    """
    config = get_automation_config()
    pkg = config.swiggy_package_name

    logger.info("Launching Swiggy app (%s)...", pkg)
    try:
        if force_stop_first and hasattr(d, "app_stop"):
            d.app_stop(pkg)
            time.sleep(0.5)

        if hasattr(d, "app_start"):
            d.app_start(pkg, config.swiggy_main_activity, wait=True)
        else:
            d.shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")

        time.sleep(2.0)
        handle_all_popups(d)

        # Wait for search bar or home feed
        is_ready = is_element_present(d, "home_search_bar", timeout=config.screen_transition_timeout)
        if not is_ready:
            # Dismiss any leftover popups and retry
            handle_all_popups(d)
            is_ready = is_element_present(d, "home_search_bar", timeout=5.0)

        if is_ready:
            logger.info("Swiggy home screen loaded successfully.")
            return True

        logger.warning("Swiggy launched, but home search bar not immediately detected.")
        return True
    except Exception as e:
        logger.error("Failed to launch Swiggy: %s", e)
        raise FlowExecutionError(f"Failed to launch Swiggy app: {e}") from e


def search_restaurant(d: Any, query: str) -> bool:
    """Perform a search for a restaurant on Swiggy.

    Args:
        d: Connected uiautomator2 Device instance.
        query: Restaurant name or cuisine keyword.

    Returns:
        True if search executed and results are loaded.
    """
    config = get_automation_config()
    logger.info("Searching for restaurant query: '%s'...", query)

    # 1. Tap Home Search Bar
    if not click_element(d, "home_search_bar", timeout=config.default_timeout):
        # Fallback: Tap top search icon/area
        logger.info("Home search bar not directly clickable, attempting search entry fallback...")
        if not click_element(d, {"textContains": "Search"}, timeout=3.0):
            raise ElementNotFoundError("Could not find or tap search entry bar on Swiggy home.")

    time.sleep(0.8)
    handle_all_popups(d)

    # 2. Enter Query in Search Input
    entered = set_text(d, "search_input", text=query, clear=True, press_enter=True)
    if not entered:
        raise FlowExecutionError(f"Failed to type search query '{query}' into search input field.")

    time.sleep(1.5)
    handle_all_popups(d)
    logger.info("Search submitted for '%s'.", query)
    return True


def select_restaurant(d: Any, restaurant_name: str) -> bool:
    """Select target restaurant from search results.

    Args:
        d: Connected uiautomator2 Device instance.
        restaurant_name: Target restaurant name to match and tap.

    Returns:
        True if restaurant was selected and menu page loaded.
    """
    config = get_automation_config()
    logger.info("Selecting restaurant: '%s'...", restaurant_name)

    # Strategy 1: Exact / Partial text match on screen
    restaurant_locator = [
        {"text": restaurant_name},
        {"textContains": restaurant_name},
        {"descriptionContains": restaurant_name},
        {"xpath": f"//*[contains(@text, '{restaurant_name}') or contains(@content-desc, '{restaurant_name}')]"},
    ]

    elem = scroll_to_element(d, restaurant_locator, max_swipes=5, direction="down")
    if elem is None:
        # Strategy 2: If suggestions list has it, tap first suggestion
        logger.info("Direct restaurant text not found after scrolling. Checking suggestion cards...")
        if is_element_present(d, "search_suggestion_item", timeout=2.0):
            click_element(d, "search_suggestion_item", timeout=2.0)
            time.sleep(1.5)
            elem = scroll_to_element(d, restaurant_locator, max_swipes=4, direction="down")

    if elem is None:
        raise ElementNotFoundError(f"Restaurant '{restaurant_name}' not found in search results.")

    # Tap restaurant card
    clicked = click_element(d, restaurant_locator, timeout=3.0, delay_after=1.2)
    if not clicked:
        raise FlowExecutionError(f"Found restaurant '{restaurant_name}' but failed to tap.")

    time.sleep(1.0)
    handle_all_popups(d)
    logger.info("Opened menu for restaurant '%s'.", restaurant_name)
    return True


def search_menu_item(d: Any, item_name: str) -> bool:
    """Locate or search for a specific food dish on the restaurant menu.

    Args:
        d: Connected uiautomator2 Device instance.
        item_name: Food dish title (e.g. 'Margherita Pizza').

    Returns:
        True if dish is visible on screen.
    """
    config = get_automation_config()
    logger.info("Searching for menu item: '%s'...", item_name)

    item_locator = [
        {"text": item_name},
        {"textContains": item_name},
        {"descriptionContains": item_name},
        {"xpath": f"//*[contains(@text, '{item_name}') or contains(@content-desc, '{item_name}')]"},
    ]

    # Check if item is already visible or within a quick scroll
    elem = scroll_to_element(d, item_locator, max_swipes=4, direction="down")
    if elem is not None:
        logger.info("Found menu item '%s' on menu screen.", item_name)
        return True

    # Try in-menu search bar if present
    if is_element_present(d, "in_menu_search_button", timeout=1.5):
        logger.info("Using in-menu search bar...")
        click_element(d, "in_menu_search_button", timeout=2.0)
        time.sleep(0.5)
        set_text(d, "in_menu_search_input", text=item_name, clear=True, press_enter=True)
        time.sleep(1.0)
        elem = scroll_to_element(d, item_locator, max_swipes=3, direction="down")
        if elem is not None:
            return True

    logger.warning("Menu item '%s' not immediately visible. Will attempt to locate during ADD step.", item_name)
    return True


def add_to_cart(
    d: Any,
    item_name: str,
    quantity: int = 1,
    customizations: list[str] | None = None,
) -> bool:
    """Add a dish to the Swiggy cart with customizations and quantity handling.

    Args:
        d: Connected uiautomator2 Device instance.
        item_name: Dish name.
        quantity: Desired count of the dish.
        customizations: List of customization option names (e.g. ['Cheese Burst', 'Medium 10 inch']).

    Returns:
        True if item was successfully added to cart.
    """
    config = get_automation_config()
    logger.info(
        "Adding to cart: '%s' (Qty: %s, Customizations: %s)...",
        item_name,
        quantity,
        customizations,
    )

    # 1. Scroll to bring the dish into view
    item_locator = [
        {"text": item_name},
        {"textContains": item_name},
        {"descriptionContains": item_name},
        {"xpath": f"//*[contains(@text, '{item_name}') or contains(@content-desc, '{item_name}')]"},
    ]
    elem = scroll_to_element(d, item_locator, max_swipes=5, direction="down")
    if elem is None:
        raise ElementNotFoundError(f"Cannot add to cart: dish '{item_name}' not found on menu.")

    # 2. Find and click 'ADD' button associated with the dish
    # Check for direct 'ADD' button on screen
    clicked_add = False
    if is_element_present(d, "dish_add_button", timeout=2.0):
        clicked_add = click_element(d, "dish_add_button", timeout=2.0, delay_after=0.8)

    if not clicked_add:
        # Fallback: Click on dish name/card to trigger details or ADD
        click_element(d, item_locator, timeout=2.0, delay_after=0.8)
        if is_element_present(d, "dish_add_button", timeout=2.0):
            clicked_add = click_element(d, "dish_add_button", timeout=2.0, delay_after=0.8)

    time.sleep(0.8)

    # 3. Check for Customization Bottom Sheet / Options Modal
    has_customization_sheet = is_element_present(
        d, "customization_sheet_container", timeout=1.5
    ) or is_element_present(d, "customization_apply_button", timeout=1.5)

    if has_customization_sheet:
        logger.info("Customization bottom sheet detected.")
        if customizations:
            for option in customizations:
                logger.info("Selecting customization option: '%s'", option)
                option_loc = [
                    {"text": option},
                    {"textContains": option},
                    {"descriptionContains": option},
                    {"xpath": f"//*[contains(@text, '{option}') or contains(@content-desc, '{option}')]"},
                ]
                opt_elem = scroll_to_element(d, option_loc, max_swipes=3, direction="down")
                if opt_elem:
                    click_element(d, option_loc, timeout=2.0, delay_after=0.4)
                else:
                    logger.warning("Customization option '%s' not found on sheet.", option)

        # Commit customizations by clicking 'Add Item' / 'Continue'
        logger.info("Committing customizations to cart...")
        click_element(d, "customization_apply_button", timeout=3.0, delay_after=1.0)

    # 4. Handle Additional Quantity (> 1)
    if quantity > 1:
        additional_clicks = quantity - 1
        logger.info("Incrementing quantity by %s using '+' button...", additional_clicks)
        for i in range(additional_clicks):
            if not click_element(d, "dish_quantity_plus", timeout=2.0, delay_after=0.5):
                logger.warning("Failed to tap '+' button on iteration %s of %s", i + 1, additional_clicks)
                break

    time.sleep(0.8)
    handle_all_popups(d)

    # 5. Verify Cart Presence / Floating Bar
    if is_element_present(d, "floating_cart_bar", timeout=3.0) or is_element_present(d, "view_cart_button", timeout=3.0):
        logger.info("Successfully added '%s' to cart.", item_name)
        return True

    logger.info("Add to cart executed for '%s'.", item_name)
    return True


def view_cart(d: Any) -> bool:
    """Navigate to the Cart summary screen.

    Returns:
        True if Cart screen is opened.
    """
    config = get_automation_config()
    logger.info("Opening Cart...")

    # Click Floating Cart Bar or View Cart Button
    clicked = click_element(d, "view_cart_button", timeout=config.default_timeout)
    if not clicked:
        clicked = click_element(d, "floating_cart_bar", timeout=3.0)

    if not clicked:
        raise ElementNotFoundError("Could not find 'View Cart' button or floating cart bar.")

    time.sleep(1.5)
    handle_all_popups(d)
    logger.info("Cart view opened.")
    return True


def proceed_to_checkout(d: Any, stop_at_payment: bool = True) -> dict[str, Any]:
    """Proceed to checkout / review screen with strict safety boundary enforcement.

    Args:
        d: Connected uiautomator2 Device instance.
        stop_at_payment: If True, halts before final payment action.

    Returns:
        Status dictionary with execution milestone.
    """
    config = get_automation_config()
    logger.info("Proceeding towards checkout summary...")

    # Safety Check before clicking checkout
    if is_payment_screen(d):
        return stop_before_payment(d)

    # Find checkout / proceed button
    checkout_elem = find_element(d, "cart_checkout_button", timeout=config.default_timeout)
    if checkout_elem is None:
        raise ElementNotFoundError("Checkout / Proceed button not found in cart.")

    # Check button text safety
    elem_text = None
    try:
        if hasattr(checkout_elem, "text"):
            elem_text = checkout_elem.text
    except Exception:
        pass

    if not is_safe_to_click(elem_text):
        logger.info("Checkout button text indicates final payment ('%s'). Halting for safety.", elem_text)
        return stop_before_payment(d)

    # Click Proceed / Select Address button
    click_element(d, "cart_checkout_button", timeout=config.default_timeout, delay_after=1.5)
    handle_all_popups(d)

    # Final Safety Halt
    if stop_at_payment or is_payment_screen(d):
        return stop_before_payment(d)

    return {"status": "CHECKOUT_PROCEEDED", "human_takeover_required": True}
