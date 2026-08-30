"""Multi-strategy element locators for Swiggy Android App.

Each locator key maps to an ordered list of locator strategies (resourceId,
text, textContains, textMatches, description, descriptionContains, xpath, className).
This provides maximum resilience against Swiggy UI updates and A/B tests.
"""

from typing import Any

# ==============================================================================
# SWIGGY LOCATOR CATALOG
# ==============================================================================

SWIGGY_LOCATORS: dict[str, list[dict[str, Any]]] = {
    # --- Home & Search Entry ---
    "home_search_bar": [
        {"resourceId": "in.swiggy.android:id/search_icon_view"},
        {"resourceId": "in.swiggy.android:id/search_query_section"},
        {"resourceId": "in.swiggy.android:id/search_edit_text"},
        {"textContains": "Search for restaurant, item or more"},
        {"textContains": "Search for 'Pizza'"},
        {"textContains": "Search for"},
        {"descriptionContains": "Search"},
        {"xpath": "//*[contains(@text, 'Search') or contains(@content-desc, 'Search')]"},
    ],
    "search_input": [
        {"resourceId": "in.swiggy.android:id/search_query_edit_text"},
        {"resourceId": "in.swiggy.android:id/et_search"},
        {"resourceId": "in.swiggy.android:id/search_edit_text"},
        {"className": "android.widget.EditText"},
        {"xpath": "//android.widget.EditText"},
    ],
    "search_clear_button": [
        {"resourceId": "in.swiggy.android:id/search_close_btn"},
        {"resourceId": "in.swiggy.android:id/clear_search_query_btn"},
        {"descriptionContains": "Clear"},
    ],
    "search_suggestion_item": [
        {"resourceId": "in.swiggy.android:id/suggestion_title"},
        {"resourceId": "in.swiggy.android:id/search_suggestion_text"},
        {"xpath": "//android.widget.TextView[contains(@resource-id, 'suggestion')]"},
    ],

    # --- Restaurant Search Results & Menu ---
    "restaurant_card": [
        {"resourceId": "in.swiggy.android:id/restaurant_card_view"},
        {"resourceId": "in.swiggy.android:id/rest_card"},
        {"resourceId": "in.swiggy.android:id/restaurant_name"},
        {"xpath": "//android.widget.TextView[contains(@resource-id, 'restaurant_name') or contains(@resource-id, 'title')]"},
    ],
    "restaurant_title": [
        {"resourceId": "in.swiggy.android:id/restaurant_name"},
        {"resourceId": "in.swiggy.android:id/tv_restaurant_name"},
        {"resourceId": "in.swiggy.android:id/restaurant_header_title"},
        {"xpath": "//android.widget.TextView[contains(@resource-id, 'restaurant_name')]"},
    ],
    "in_menu_search_button": [
        {"resourceId": "in.swiggy.android:id/menu_search_icon"},
        {"resourceId": "in.swiggy.android:id/search_in_menu"},
        {"textContains": "Search in menu"},
        {"textContains": "Search dish"},
        {"descriptionContains": "Search in menu"},
    ],
    "in_menu_search_input": [
        {"resourceId": "in.swiggy.android:id/menu_search_edit_text"},
        {"resourceId": "in.swiggy.android:id/et_menu_search"},
        {"className": "android.widget.EditText"},
    ],

    # --- Dish & Cart Actions ---
    "dish_title": [
        {"resourceId": "in.swiggy.android:id/item_name"},
        {"resourceId": "in.swiggy.android:id/dish_title"},
        {"resourceId": "in.swiggy.android:id/tv_item_name"},
        {"xpath": "//android.widget.TextView[contains(@resource-id, 'item_name') or contains(@resource-id, 'dish_title')]"},
    ],
    "dish_add_button": [
        {"text": "ADD"},
        {"text": "Add"},
        {"textMatches": "^(?i)add$"},
        {"resourceId": "in.swiggy.android:id/add_to_cart_btn"},
        {"resourceId": "in.swiggy.android:id/add_btn"},
        {"resourceId": "in.swiggy.android:id/btn_add"},
        {"descriptionContains": "Add to cart"},
        {"xpath": "//*[@text='ADD' or @text='Add' or contains(@text, 'ADD')]"},
    ],
    "dish_quantity_plus": [
        {"resourceId": "in.swiggy.android:id/btn_plus"},
        {"resourceId": "in.swiggy.android:id/quantity_add"},
        {"resourceId": "in.swiggy.android:id/increment_btn"},
        {"text": "+"},
        {"descriptionContains": "Increase"},
        {"descriptionContains": "Add more"},
        {"xpath": "//*[@text='+' or contains(@content-desc, 'Increase') or contains(@content-desc, 'plus')]"},
    ],
    "dish_quantity_minus": [
        {"resourceId": "in.swiggy.android:id/btn_minus"},
        {"resourceId": "in.swiggy.android:id/quantity_subtract"},
        {"text": "-"},
        {"text": "−"},
        {"descriptionContains": "Decrease"},
    ],

    # --- Customization Sheet ---
    "customization_sheet_container": [
        {"resourceId": "in.swiggy.android:id/customise_bottom_sheet"},
        {"resourceId": "in.swiggy.android:id/customisation_bottom_sheet"},
        {"resourceId": "in.swiggy.android:id/design_bottom_sheet"},
        {"textContains": "Customise as per your taste"},
        {"textContains": "Customise"},
        {"textContains": "Customisation"},
    ],
    "customization_option_radio": [
        {"className": "android.widget.RadioButton"},
        {"resourceId": "in.swiggy.android:id/radio_button"},
        {"resourceId": "in.swiggy.android:id/rb_option"},
    ],
    "customization_option_checkbox": [
        {"className": "android.widget.CheckBox"},
        {"resourceId": "in.swiggy.android:id/checkbox"},
        {"resourceId": "in.swiggy.android:id/cb_option"},
    ],
    "customization_apply_button": [
        {"textMatches": "(?i).*add item.*"},
        {"textMatches": "(?i).*continue.*"},
        {"textMatches": "(?i).*apply.*"},
        {"textMatches": "(?i).*add to cart.*"},
        {"resourceId": "in.swiggy.android:id/btn_add_customised_item"},
        {"resourceId": "in.swiggy.android:id/add_item_btn"},
        {"resourceId": "in.swiggy.android:id/btn_continue"},
        {"xpath": "//*[contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add item') or contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"},
    ],

    # --- Floating Cart Bar & Cart Screen ---
    "floating_cart_bar": [
        {"resourceId": "in.swiggy.android:id/cart_floating_view"},
        {"resourceId": "in.swiggy.android:id/view_cart_layout"},
        {"resourceId": "in.swiggy.android:id/cart_strip"},
        {"textContains": "View Cart"},
        {"textContains": "VIEW CART"},
        {"descriptionContains": "View Cart"},
        {"xpath": "//*[contains(@text, 'View Cart') or contains(@text, 'VIEW CART')]"},
    ],
    "view_cart_button": [
        {"text": "VIEW CART"},
        {"text": "View Cart"},
        {"textContains": "View Cart"},
        {"resourceId": "in.swiggy.android:id/view_cart_btn"},
        {"resourceId": "in.swiggy.android:id/btn_view_cart"},
        {"resourceId": "in.swiggy.android:id/tv_view_cart"},
        {"xpath": "//*[@text='VIEW CART' or @text='View Cart' or contains(@text, 'View Cart')]"},
    ],
    "cart_checkout_button": [
        {"textMatches": "(?i).*proceed to pay.*"},
        {"textMatches": "(?i).*select address.*"},
        {"textMatches": "(?i).*proceed to checkout.*"},
        {"textMatches": "(?i).*review order.*"},
        {"resourceId": "in.swiggy.android:id/proceed_to_checkout_btn"},
        {"resourceId": "in.swiggy.android:id/btn_checkout"},
        {"resourceId": "in.swiggy.android:id/pay_button"},
    ],
    "cart_item_row": [
        {"resourceId": "in.swiggy.android:id/cart_item_name"},
        {"resourceId": "in.swiggy.android:id/item_title"},
        {"xpath": "//android.widget.TextView[contains(@resource-id, 'cart_item_name')]"},
    ],

    # --- Popups & Overlays ---
    "location_allow_button": [
        {"resourceId": "com.android.permissioncontroller:id/permission_allow_foreground_only_button"},
        {"resourceId": "com.android.permissioncontroller:id/permission_allow_one_time_button"},
        {"text": "While using the app"},
        {"text": "Only this time"},
        {"text": "Allow"},
        {"text": "ALLOW"},
        {"textContains": "While using"},
    ],
    "location_deny_button": [
        {"resourceId": "com.android.permissioncontroller:id/permission_deny_button"},
        {"text": "Don't allow"},
        {"text": "Deny"},
        {"text": "DENY"},
    ],
    "notification_allow_button": [
        {"resourceId": "com.android.permissioncontroller:id/permission_allow_button"},
        {"text": "Allow"},
        {"text": "ALLOW"},
    ],
    "notification_deny_button": [
        {"resourceId": "com.android.permissioncontroller:id/permission_deny_button"},
        {"text": "Don't allow"},
        {"text": "Not now"},
    ],
    "generic_close_button": [
        {"resourceId": "in.swiggy.android:id/close_button"},
        {"resourceId": "in.swiggy.android:id/iv_close"},
        {"resourceId": "in.swiggy.android:id/btn_close"},
        {"resourceId": "in.swiggy.android:id/cross_icon"},
        {"description": "Close"},
        {"description": "close"},
        {"text": "✕"},
        {"text": "×"},
        {"text": "Skip"},
        {"text": "Not Now"},
        {"text": "Later"},
    ],
    "address_confirm_button": [
        {"textContains": "Confirm Location"},
        {"textContains": "Use Current Location"},
        {"textContains": "Deliver Here"},
        {"resourceId": "in.swiggy.android:id/confirm_location_btn"},
    ],

    # --- Payment / Safety Boundary Indicators ---
    "payment_screen_indicators": [
        {"textMatches": "(?i).*pay ₹.*"},
        {"textMatches": "(?i).*pay now.*"},
        {"textMatches": "(?i).*payment options.*"},
        {"textMatches": "(?i).*select payment method.*"},
        {"textMatches": "(?i).*upi.*"},
        {"textMatches": "(?i).*google pay.*"},
        {"textMatches": "(?i).*phonepe.*"},
        {"textMatches": "(?i).*paytm.*"},
        {"textMatches": "(?i).*credit / debit card.*"},
        {"textMatches": "(?i).*net banking.*"},
        {"textMatches": "(?i).*enter pin.*"},
        {"textMatches": "(?i).*enter upi pin.*"},
        {"textMatches": "(?i).*enter otp.*"},
        {"resourceId": "in.swiggy.android:id/payment_header"},
        {"resourceId": "in.swiggy.android:id/payment_methods_container"},
    ],
}


def get_locator_strategies(locator_key: str) -> list[dict[str, Any]]:
    """Retrieve the list of locator strategies for a given element identifier.

    Args:
        locator_key: Identifier key from SWIGGY_LOCATORS.

    Returns:
        List of locator strategy dictionaries.
    """
    if locator_key not in SWIGGY_LOCATORS:
        raise KeyError(f"Locator key '{locator_key}' not found in SWIGGY_LOCATORS catalog.")
    return SWIGGY_LOCATORS[locator_key]
