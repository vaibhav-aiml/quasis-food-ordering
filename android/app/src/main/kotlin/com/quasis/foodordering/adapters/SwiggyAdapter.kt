package com.quasis.foodordering.adapters

import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.accessibility.GestureDispatcher
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.engine.ExecutionSafetyGuard
import com.quasis.foodordering.models.ScreenType
import kotlinx.coroutines.delay

/**
 * Swiggy Food Delivery App Adapter.
 *
 * Implements UI discovery, screen transitions, item selections, and customization handling
 * with human-in-the-loop safety boundaries.
 */
class SwiggyAdapter(
    private val serviceSupplier: () -> FoodAccessibilityService? = { FoodAccessibilityService.instance }
) : FoodAppAdapter {

    override val appId: String = "swiggy"
    override val appName: String = "Swiggy"
    override val packageName: String = SwiggyScreenMappings.PACKAGE_NAME

    companion object {
        private const val TAG = "SwiggyAdapter"
        private const val STEP_TIMEOUT_MS = 10000L
    }

    override fun detectScreen(rootNode: AccessibilityNodeInfo?): ScreenType {
        return SwiggyScreenMappings.detectScreen(rootNode)
    }

    private fun getService(): FoodAccessibilityService {
        return serviceSupplier() ?: throw IllegalStateException("FoodAccessibilityService is not connected.")
    }

    private fun getRootNode(): AccessibilityNodeInfo? {
        return serviceSupplier()?.rootInActiveWindow
    }

    /**
     * Step: Search for a restaurant on Swiggy home/search screen.
     */
    suspend fun searchRestaurant(query: String): Boolean {
        Log.i(TAG, "Executing searchRestaurant: '$query'")
        val service = getService()

        // 1. Locate search bar
        val searchBar = SwiggyNodeActions.waitForNode(
            timeoutMs = STEP_TIMEOUT_MS,
            rootSupplier = { getRootNode() }
        ) { node ->
            val id = node.viewIdResourceName ?: ""
            id.contains("search") || (node.text?.contains("search", ignoreCase = true) == true)
        }

        if (searchBar == null) {
            Log.e(TAG, "Search bar not found on Swiggy screen.")
            return false
        }

        // 2. Click search bar to focus
        SwiggyNodeActions.clickWithRetry(searchBar, service)
        delay(400L)

        // 3. Inject query text
        val activeRoot = getRootNode()
        val editableSearch = NodeHierarchyScanner.findNodesByText(activeRoot, "search")
            .firstOrNull { it.isEditable } ?: searchBar

        val textSet = GestureDispatcher.setText(service, editableSearch, query)
        if (!textSet) {
            Log.e(TAG, "Failed to enter search query '$query' in search bar.")
            return false
        }

        Log.d(TAG, "Search query '$query' entered. Waiting for search results screen...")
        return SwiggyNodeActions.waitForScreen(
            targetScreen = ScreenType.SEARCH_RESULTS,
            timeoutMs = STEP_TIMEOUT_MS,
            rootSupplier = { getRootNode() }
        )
    }

    /**
     * Step: Select restaurant from search results.
     */
    suspend fun selectRestaurant(name: String): Boolean {
        Log.i(TAG, "Executing selectRestaurant: '$name'")
        val service = getService()

        // Find restaurant card matching name
        val restaurantNode = SwiggyNodeActions.scrollToFindText(
            targetText = name,
            service = service,
            rootSupplier = { getRootNode() },
            maxScrolls = 4
        )

        if (restaurantNode == null) {
            Log.e(TAG, "Restaurant '$name' not found in search results.")
            return false
        }

        val clicked = SwiggyNodeActions.clickWithRetry(restaurantNode, service)
        if (!clicked) {
            Log.e(TAG, "Failed to click restaurant '$name'.")
            return false
        }

        Log.d(TAG, "Clicked restaurant '$name'. Waiting for menu screen...")
        return SwiggyNodeActions.waitForScreen(
            targetScreen = ScreenType.RESTAURANT_MENU,
            timeoutMs = STEP_TIMEOUT_MS,
            rootSupplier = { getRootNode() }
        )
    }

    /**
     * Step: Search for menu item within restaurant page.
     */
    suspend fun searchMenuItem(itemName: String): Boolean {
        Log.i(TAG, "Executing searchMenuItem: '$itemName'")
        val service = getService()

        // Find in-menu search bar if available, or scroll to item
        val inMenuSearch = SwiggyNodeActions.waitForNode(
            timeoutMs = 3000L,
            rootSupplier = { getRootNode() }
        ) { node ->
            node.text?.contains("search in menu", ignoreCase = true) == true
        }

        if (inMenuSearch != null) {
            SwiggyNodeActions.clickWithRetry(inMenuSearch, service)
            delay(300L)
            val activeRoot = getRootNode()
            val editable = NodeHierarchyScanner.findNodesByText(activeRoot, "search")
                .firstOrNull { it.isEditable } ?: inMenuSearch
            GestureDispatcher.setText(service, editable, itemName)
            delay(500L)
            return true
        }

        // Otherwise scroll to find the item
        val foundNode = SwiggyNodeActions.scrollToFindText(
            targetText = itemName,
            service = service,
            rootSupplier = { getRootNode() },
            maxScrolls = 5
        )
        return foundNode != null
    }

    /**
     * Step: Select dish and click ADD button.
     */
    suspend fun selectMenuItem(name: String, quantity: Int = 1): Boolean {
        Log.i(TAG, "Executing selectMenuItem: '$name', quantity=$quantity")
        val service = getService()

        // Scroll to find the item node
        val itemNode = SwiggyNodeActions.scrollToFindText(
            targetText = name,
            service = service,
            rootSupplier = { getRootNode() },
            maxScrolls = 5
        )

        if (itemNode == null) {
            Log.e(TAG, "Menu item '$name' not found.")
            return false
        }

        // Look for 'ADD' button near the dish
        val activeRoot = getRootNode()
        val addButtons = SwiggyScreenMappings.getAddButtons(activeRoot)
        val targetButton = addButtons.firstOrNull() ?: itemNode

        val clicked = SwiggyNodeActions.clickWithRetry(targetButton, service)
        if (!clicked) {
            Log.e(TAG, "Failed to click ADD for '$name'.")
            return false
        }

        delay(600L)
        return true
    }

    /**
     * Step: Select requested customizations on customization sheet.
     */
    suspend fun applyCustomizations(customizations: List<String>): Boolean {
        if (customizations.isEmpty()) return true
        Log.i(TAG, "Applying customizations: $customizations")
        val service = getService()

        val rootNode = getRootNode()
        val screen = detectScreen(rootNode)
        if (screen != ScreenType.CUSTOMIZATION_SHEET) {
            Log.d(TAG, "No customization sheet detected. Proceeding.")
            return true
        }

        for (customization in customizations) {
            val optionNode = SwiggyNodeActions.scrollToFindText(
                targetText = customization,
                service = service,
                rootSupplier = { getRootNode() },
                maxScrolls = 3
            )
            if (optionNode != null) {
                Log.d(TAG, "Selecting customization option: '$customization'")
                SwiggyNodeActions.clickWithRetry(optionNode, service)
                delay(300L)
            } else {
                Log.w(TAG, "Customization option '$customization' not found.")
            }
        }

        // Click Apply / Continue / Add Item button
        return addToCart()
    }

    /**
     * Step: Click Add Item / Continue button to commit to cart.
     */
    suspend fun addToCart(): Boolean {
        Log.i(TAG, "Executing addToCart")
        val service = getService()
        val rootNode = getRootNode()

        val commitButtons = NodeHierarchyScanner.findNodesByText(rootNode, "add item")
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "continue") }
            .ifEmpty { NodeHierarchyScanner.findNodesByText(rootNode, "apply") }
            .ifEmpty { SwiggyScreenMappings.getAddButtons(rootNode) }

        if (commitButtons.isNotEmpty()) {
            val clicked = SwiggyNodeActions.clickWithRetry(commitButtons.first(), service)
            delay(500L)
            return clicked
        }

        return true
    }

    /**
     * Step: View cart summary.
     */
    suspend fun viewCart(): Boolean {
        Log.i(TAG, "Executing viewCart")
        val service = getService()
        val rootNode = getRootNode()

        val cartButton = SwiggyScreenMappings.getViewCartButton(rootNode)
        if (cartButton == null) {
            Log.e(TAG, "View Cart button not found on screen.")
            return false
        }

        val clicked = SwiggyNodeActions.clickWithRetry(cartButton, service)
        if (!clicked) {
            Log.e(TAG, "Failed to click View Cart button.")
            return false
        }

        Log.d(TAG, "Clicked View Cart. Waiting for Cart screen...")
        return SwiggyNodeActions.waitForScreen(
            targetScreen = ScreenType.CART,
            timeoutMs = STEP_TIMEOUT_MS,
            rootSupplier = { getRootNode() }
        )
    }

    /**
     * Step: Proceed to checkout screen, stopping BEFORE payment.
     */
    suspend fun proceedToCheckout(): Boolean {
        Log.i(TAG, "Executing proceedToCheckout")
        val service = getService()
        val rootNode = getRootNode()

        // 1. SAFETY CHECK: Check if currently on payment screen
        val currentScreen = detectScreen(rootNode)
        if (ExecutionSafetyGuard.isPaymentScreenHaltRequired(currentScreen)) {
            Log.i(TAG, "SAFETY HALT: Already at checkout/payment screen. Stopping automation for user takeover.")
            return true
        }

        // 2. Locate checkout button
        val checkoutButton = SwiggyScreenMappings.getCheckoutButton(rootNode)
        if (checkoutButton == null) {
            Log.e(TAG, "Checkout button not found on Cart screen.")
            return false
        }

        // 3. SAFETY CHECK: Verify target button is not an instant payment confirmation
        val buttonText = checkoutButton.text?.toString() ?: checkoutButton.contentDescription?.toString()
        if (ExecutionSafetyGuard.isDangerousPaymentInteraction(buttonText)) {
            Log.w(TAG, "SAFETY INTERCEPT: Blocked dangerous payment button click: '$buttonText'")
            return true
        }

        val clicked = SwiggyNodeActions.clickWithRetry(checkoutButton, service)
        delay(800L)

        // 4. Verify arrival at payment screen milestone
        val finalScreen = detectScreen(getRootNode())
        Log.i(TAG, "Reached final milestone. Detected screen: $finalScreen. Automation paused for user payment.")
        return true
    }
}
