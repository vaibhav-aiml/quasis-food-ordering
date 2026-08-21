package com.quasis.foodordering.adapters

import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.models.ScreenType

/**
 * Screen type detection rules, resource IDs, and element finders for Swiggy Android application.
 */
object SwiggyScreenMappings {

    const val PACKAGE_NAME = "in.swiggy.android"

    // Common Swiggy View Resource IDs
    object ResourceIds {
        const val SEARCH_EDIT_TEXT = "in.swiggy.android:id/search_edit_text"
        const val SEARCH_BOX = "in.swiggy.android:id/search_box"
        const val SEARCH_HINT = "in.swiggy.android:id/search_hint_text"
        const val RESTAURANT_NAME = "in.swiggy.android:id/restaurant_name"
        const val RESTAURANT_CARD = "in.swiggy.android:id/restaurant_card"
        const val MENU_ITEM_NAME = "in.swiggy.android:id/menu_item_name"
        const val ITEM_TITLE = "in.swiggy.android:id/item_title"
        const val ADD_BUTTON = "in.swiggy.android:id/add_button"
        const val BTN_ADD = "in.swiggy.android:id/btn_add"
        const val VIEW_CART_BUTTON = "in.swiggy.android:id/view_cart_button"
        const val FLOATING_CART = "in.swiggy.android:id/floating_cart_layout"
        const val CHECKOUT_BUTTON = "in.swiggy.android:id/checkout_button"
        const val PROCEED_TO_PAY = "in.swiggy.android:id/proceed_to_pay"
        const val PAY_NOW_BUTTON = "in.swiggy.android:id/pay_now_button"
    }

    /**
     * Detects Swiggy's active UI screen state from node hierarchy.
     */
    fun detectScreen(rootNode: AccessibilityNodeInfo?): ScreenType {
        if (rootNode == null) return ScreenType.UNKNOWN

        val texts = NodeHierarchyScanner.extractAllVisibleTexts(rootNode).map { it.lowercase() }
        val joined = texts.joinToString(" ")

        // 1. Payment Gateway / Payment Options (CRITICAL SAFETY SCREEN)
        if (isPaymentScreen(joined, texts, rootNode)) {
            return ScreenType.CHECKOUT_PAYMENT
        }

        // 2. Cart / Review Order Screen
        if (isCartScreen(joined, texts, rootNode)) {
            return ScreenType.CART
        }

        // 3. Customization Bottom Sheet
        if (isCustomizationSheet(joined, texts, rootNode)) {
            return ScreenType.CUSTOMIZATION_SHEET
        }

        // 4. Restaurant Menu Screen
        if (isRestaurantMenuScreen(joined, texts, rootNode)) {
            return ScreenType.RESTAURANT_MENU
        }

        // 5. Search Results Screen
        if (isSearchResultsScreen(joined, texts, rootNode)) {
            return ScreenType.SEARCH_RESULTS
        }

        // 6. Search Input Screen
        if (isSearchInputScreen(joined, texts, rootNode)) {
            return ScreenType.SEARCH
        }

        // 7. Swiggy Home Screen
        if (isHomeScreen(joined, texts, rootNode)) {
            return ScreenType.HOME
        }

        return ScreenType.UNKNOWN
    }

    fun getSearchBar(rootNode: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        if (rootNode == null) return null
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.SEARCH_EDIT_TEXT)
            .ifEmpty { NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.SEARCH_BOX) }
        if (byId.isNotEmpty()) return byId.first()

        val byText = NodeHierarchyScanner.findNodesByText(rootNode, "search for restaurant")
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "search for dishes") }
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "search") }
        return byText.firstOrNull()
    }

    fun getRestaurantCards(rootNode: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (rootNode == null) return emptyList()
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.RESTAURANT_NAME)
            .ifEmpty { NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.RESTAURANT_CARD) }
        if (byId.isNotEmpty()) return byId

        return NodeHierarchyScanner.findNodesByText(rootNode, "mins", exactMatch = false)
    }

    fun getMenuItems(rootNode: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (rootNode == null) return emptyList()
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.MENU_ITEM_NAME)
            .ifEmpty { NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.ITEM_TITLE) }
        if (byId.isNotEmpty()) return byId

        return NodeHierarchyScanner.findNodesByText(rootNode, "₹", exactMatch = false)
    }

    fun getAddButtons(rootNode: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (rootNode == null) return emptyList()
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.ADD_BUTTON)
            .ifEmpty { NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.BTN_ADD) }
        if (byId.isNotEmpty()) return byId

        return NodeHierarchyScanner.findNodesByText(rootNode, "add", exactMatch = true)
    }

    fun getViewCartButton(rootNode: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        if (rootNode == null) return null
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.VIEW_CART_BUTTON)
            .ifEmpty { NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.FLOATING_CART) }
        if (byId.isNotEmpty()) return byId.first()

        val byText = NodeHierarchyScanner.findNodesByText(rootNode, "view cart")
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "items added") }
        return byText.firstOrNull()
    }

    fun getCheckoutButton(rootNode: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        if (rootNode == null) return null
        val byId = NodeHierarchyScanner.findNodesByResourceId(rootNode, ResourceIds.CHECKOUT_BUTTON)
        if (byId.isNotEmpty()) return byId.first()

        val byText = NodeHierarchyScanner.findNodesByText(rootNode, "proceed to checkout")
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "checkout") }
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "select address") }
        return byText.firstOrNull()
    }

    // --- Private Matcher Rules ---

    private fun isPaymentScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val paymentKeywords = listOf(
            "pay using", "payment options", "upi", "google pay", "phonepe",
            "credit/debit cards", "wallets", "total to pay", "pay now",
            "proceed to pay", "make payment", "payment gateway"
        )
        return paymentKeywords.any { joined.contains(it) }
    }

    private fun isCartScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val cartKeywords = listOf(
            "bill details", "to pay", "item total", "delivery partner tip",
            "cancellation policy", "apply coupon", "view cart", "review order"
        )
        return cartKeywords.any { joined.contains(it) }
    }

    private fun isCustomizationSheet(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val customKeywords = listOf(
            "customize", "choose quantity", "choose portion", "add item",
            "repeat last", "customise", "required", "choose 1", "add-on"
        )
        return customKeywords.any { joined.contains(it) }
    }

    private fun isRestaurantMenuScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val menuKeywords = listOf(
            "search in menu", "recommended", "bestseller", "menu",
            "pure veg", "starters", "main course", "combos"
        )
        return menuKeywords.any { joined.contains(it) }
    }

    private fun isSearchResultsScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val resultsKeywords = listOf(
            "restaurants", "dishes", "showing results for", "filter & sort",
            "delivery time", "rating 4.0+"
        )
        return resultsKeywords.any { joined.contains(it) }
    }

    private fun isSearchInputScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val searchKeywords = listOf(
            "search for restaurant", "search for dishes", "trending searches",
            "recent searches", "search food"
        )
        return searchKeywords.any { joined.contains(it) }
    }

    private fun isHomeScreen(joined: String, texts: List<String>, rootNode: AccessibilityNodeInfo): Boolean {
        val homeKeywords = listOf(
            "delivery to", "what's on your mind", "food delivery",
            "top brands", "offers for you", "restaurants near you",
            "swiggy dineout", "instamart"
        )
        return homeKeywords.any { joined.contains(it) }
    }
}
