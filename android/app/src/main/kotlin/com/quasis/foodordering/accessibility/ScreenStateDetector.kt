package com.quasis.foodordering.accessibility

import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.models.ScreenType

/**
 * Detects current application screen state from visible accessibility node hierarchy.
 */
object ScreenStateDetector {

    /**
     * Determines the ScreenType by matching signature text patterns and resource elements.
     */
    fun detectScreen(root: AccessibilityNodeInfo?): ScreenType {
        if (root == null) return ScreenType.UNKNOWN

        val visibleTexts = NodeHierarchyScanner.extractAllVisibleTexts(root)
            .map { it.lowercase() }
        val joined = visibleTexts.joinToString(" ")

        // 1. Checkout & Payment detection (highest priority for safety)
        if (isPaymentOrCheckoutScreen(joined, visibleTexts)) {
            return ScreenType.CHECKOUT_PAYMENT
        }

        // 2. Cart Summary detection
        if (isCartScreen(joined, visibleTexts)) {
            return ScreenType.CART
        }

        // 3. Customization Bottom Sheet detection
        if (isCustomizationSheet(joined, visibleTexts)) {
            return ScreenType.CUSTOMIZATION_SHEET
        }

        // 4. Restaurant Menu Page detection
        if (isRestaurantMenuScreen(joined, visibleTexts)) {
            return ScreenType.RESTAURANT_MENU
        }

        // 5. Search Results detection
        if (isSearchResultsScreen(joined, visibleTexts)) {
            return ScreenType.SEARCH_RESULTS
        }

        // 6. Search Bar / Search Home detection
        if (isSearchScreen(joined, visibleTexts)) {
            return ScreenType.SEARCH
        }

        // 7. App Home Page detection
        if (isHomeScreen(joined, visibleTexts)) {
            return ScreenType.HOME
        }

        return ScreenType.UNKNOWN
    }

    private fun isPaymentOrCheckoutScreen(joined: String, texts: List<String>): Boolean {
        val paymentKeywords = listOf(
            "pay using", "payment options", "upi", "credit/debit cards",
            "netbanking", "wallets", "total to pay", "pay now",
            "proceed to pay", "make payment", "payment gateway"
        )
        return paymentKeywords.any { joined.contains(it) }
    }

    private fun isCartScreen(joined: String, texts: List<String>): Boolean {
        // "view cart" excluded on purpose — also appears on the RESTAURANT_MENU screen's floating cart bar
        val cartKeywords = listOf(
            "bill details", "to pay", "item total", "delivery partner tip",
            "cancellation policy", "apply coupon", "review order"
        )
        return cartKeywords.any { joined.contains(it) }
    }

    private fun isCustomizationSheet(joined: String, texts: List<String>): Boolean {
        val customKeywords = listOf(
            "customize", "choose quantity", "choose portion", "add item",
            "repeat last", "customise", "required", "choose 1", "add-on"
        )
        return customKeywords.any { joined.contains(it) }
    }

    private fun isRestaurantMenuScreen(joined: String, texts: List<String>): Boolean {
        val menuKeywords = listOf(
            "search in menu", "recommended", "bestseller", "menu",
            "pure veg", "filters", "starters", "main course"
        )
        return menuKeywords.any { joined.contains(it) }
    }

    private fun isSearchResultsScreen(joined: String, texts: List<String>): Boolean {
        val resultKeywords = listOf(
            "restaurants", "dishes", "showing results for", "filter & sort"
        )
        return resultKeywords.any { joined.contains(it) }
    }

    private fun isSearchScreen(joined: String, texts: List<String>): Boolean {
        val searchKeywords = listOf(
            "search for restaurant", "search for dishes", "trending searches",
            "recent searches", "search food"
        )
        return searchKeywords.any { joined.contains(it) }
    }

    private fun isHomeScreen(joined: String, texts: List<String>): Boolean {
        val homeKeywords = listOf(
            "delivery to", "what's on your mind", "food delivery",
            "top brands", "offers for you", "restaurants near you"
        )
        return homeKeywords.any { joined.contains(it) }
    }
}
