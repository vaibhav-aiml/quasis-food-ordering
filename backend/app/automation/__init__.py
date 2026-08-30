"""Python + uiautomator2 automation module for food ordering and quick-commerce.

Provides function-based device management, multi-strategy UI element interactions,
dynamic popup suppression, end-to-end Swiggy user journeys, safety boundaries,
and plan orchestration.
"""

from app.automation.actions import (
    click_element,
    find_element,
    get_element_text,
    is_element_present,
    press_key,
    scroll_to_element,
    set_text,
    swipe,
    take_screenshot,
    wait_for_element,
)
from app.automation.config import AutomationConfig, get_automation_config
from app.automation.device_manager import (
    connect_device,
    ensure_app_installed,
    get_device_info,
    is_device_connected,
    reconnect_device,
)
from app.automation.exceptions import (
    ActionTimeoutError,
    AutomationError,
    DeviceConnectionError,
    DeviceNotFoundError,
    ElementNotFoundError,
    FlowExecutionError,
    OrderExecutionCancelled,
    PaymentScreenSafetyHalt,
    PopupInterferenceError,
)
from app.automation.locators import SWIGGY_LOCATORS, get_locator_strategies
from app.automation.orchestrator import (
    cancel_order,
    execute_order_plan,
    get_order_status,
)
from app.automation.popup_handler import (
    dismiss_address_confirmation,
    dismiss_generic_overlay,
    dismiss_location_popup,
    dismiss_notification_popup,
    handle_all_popups,
)
from app.automation.safety_guard import (
    is_payment_screen,
    is_safe_to_click,
    stop_before_payment,
    verify_safety_boundary,
)
from app.automation.swiggy_flows import (
    add_to_cart,
    launch_swiggy,
    proceed_to_checkout,
    search_menu_item,
    search_restaurant,
    select_restaurant,
    view_cart,
)

__all__ = [
    # Config & Exceptions
    "AutomationConfig",
    "get_automation_config",
    "AutomationError",
    "DeviceConnectionError",
    "DeviceNotFoundError",
    "ElementNotFoundError",
    "ActionTimeoutError",
    "PopupInterferenceError",
    "PaymentScreenSafetyHalt",
    "FlowExecutionError",
    "OrderExecutionCancelled",
    # Device Management
    "connect_device",
    "get_device_info",
    "is_device_connected",
    "ensure_app_installed",
    "reconnect_device",
    # Locators & Actions
    "SWIGGY_LOCATORS",
    "get_locator_strategies",
    "find_element",
    "wait_for_element",
    "is_element_present",
    "click_element",
    "set_text",
    "scroll_to_element",
    "get_element_text",
    "swipe",
    "press_key",
    "take_screenshot",
    # Popups
    "handle_all_popups",
    "dismiss_location_popup",
    "dismiss_notification_popup",
    "dismiss_generic_overlay",
    "dismiss_address_confirmation",
    # Safety
    "is_payment_screen",
    "verify_safety_boundary",
    "stop_before_payment",
    "is_safe_to_click",
    # Flows
    "launch_swiggy",
    "search_restaurant",
    "select_restaurant",
    "search_menu_item",
    "add_to_cart",
    "view_cart",
    "proceed_to_checkout",
    # Orchestrator
    "execute_order_plan",
    "get_order_status",
    "cancel_order",
]
