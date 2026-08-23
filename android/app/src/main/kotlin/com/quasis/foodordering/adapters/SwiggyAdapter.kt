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
        val service = serviceSupplier() ?: return null
        return service.getAppRoot(packageName) ?: service.getActiveRoot()
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
        delay(800L)  // Wait longer for search screen transition

        // 3. Wait for editable EditText to appear (up to 3s)
        var editableNode: AccessibilityNodeInfo? = null
        for (attempt in 1..6) {
            val activeRoot = getRootNode()
            if (activeRoot != null) {
                editableNode = findEditableSearchNode(activeRoot)
                if (editableNode != null) {
                    Log.d(TAG, "Found editable search node on attempt $attempt")
                    break
                }
            }
            delay(500L)
        }

        if (editableNode == null) {
            // Fallback: try any EditText on screen
            Log.w(TAG, "No editable search node found after waiting. Trying fallback...")
            val activeRoot = getRootNode()
            editableNode = activeRoot?.let { findFirstEditText(it) } ?: searchBar
        }

        // 4. Inject query text
        val textSet = GestureDispatcher.setText(service, editableNode, query)
        if (!textSet) {
            Log.e(TAG, "Failed to enter search query '$query' in search bar.")
            return false
        }

        // 5. Submit search - try pressing Enter/Search key
        delay(300L)
        try {
            // Trigger IME search action
            editableNode.performAction(AccessibilityNodeInfo.ACTION_NEXT_AT_MOVEMENT_GRANULARITY)
        } catch (e: Exception) {
            Log.d(TAG, "IME action failed, Swiggy uses live search anyway")
        }

        Log.d(TAG, "Search query '$query' entered. Waiting for search results screen...")
        return SwiggyNodeActions.waitForScreen(
            targetScreen = ScreenType.SEARCH_RESULTS,
            timeoutMs = STEP_TIMEOUT_MS,
            rootSupplier = { getRootNode() }
        )
    }

    /**
     * Find an editable node suitable for search text entry.
     */
    private fun findEditableSearchNode(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        val candidates = mutableListOf<AccessibilityNodeInfo>()
        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val cls = node.className?.toString() ?: ""
            val id = node.viewIdResourceName?.lowercase() ?: ""
            if ((node.isEditable || cls.contains("EditText", ignoreCase = true)) &&
                (id.contains("search") || id.contains("query") || id.contains("edit"))) {
                candidates.add(node)
            }
            for (i in 0 until node.childCount) traverse(node.getChild(i))
        }
        traverse(root)
        return candidates.firstOrNull()
    }

    /**
     * Find any EditText node as a last resort.
     */
    private fun findFirstEditText(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        fun traverse(node: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
            if (node == null) return null
            val cls = node.className?.toString() ?: ""
            if (cls.contains("EditText", ignoreCase = true) || node.isEditable) return node
            for (i in 0 until node.childCount) {
                val found = traverse(node.getChild(i))
                if (found != null) return found
            }
            return null
        }
        return traverse(root)
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
     * Data class representing a restaurant option found in search results.
     */
    data class RestaurantOption(
        val name: String,
        val address: String,
        val displayText: String,
        val index: Int
    )

    /**
     * Detect multiple restaurants matching the query in search results.
     * Returns list of options if multiple are found, empty list if 0 or 1.
     */
    suspend fun findMatchingRestaurants(query: String): List<RestaurantOption> {
        Log.i(TAG, "Checking for multiple restaurants matching: '$query'")
        val rootNode = getRootNode() ?: return emptyList()

        val matchingNodes = NodeHierarchyScanner.findNodesByText(rootNode, query, exactMatch = false)
            .filter { node ->
                val cls = node.className?.toString() ?: ""
                cls.contains("TextView", ignoreCase = true) && !node.isEditable
            }

        if (matchingNodes.size <= 1) {
            Log.d(TAG, "Found ${matchingNodes.size} matching restaurant(s). No disambiguation needed.")
            return emptyList()
        }

        Log.i(TAG, "Found ${matchingNodes.size} restaurants matching '$query'")
        return matchingNodes.mapIndexed { index, node ->
            val name = node.text?.toString() ?: query
            val address = extractAddressNearNode(node)
            val display = if (address.isNotEmpty()) "$name - $address" else "$name (Option ${index + 1})"
            RestaurantOption(name = name, address = address, displayText = display, index = index)
        }
    }

    /**
     * Extract address/locality text from nodes near a restaurant name.
     */
    private fun extractAddressNearNode(node: AccessibilityNodeInfo): String {
        try {
            val parent = node.parent ?: return ""
            for (i in 0 until parent.childCount) {
                val sibling = parent.getChild(i) ?: continue
                if (sibling == node) continue
                val text = sibling.text?.toString() ?: ""
                val id = sibling.viewIdResourceName?.lowercase() ?: ""
                if (id.contains("area") || id.contains("address") || id.contains("subtitle") || id.contains("location")) {
                    return text
                }
                if (text.contains(",") || text.contains("nagar", ignoreCase = true) || text.contains("road", ignoreCase = true)) {
                    return text
                }
            }
        } catch (e: Exception) {
            Log.d(TAG, "Address extraction failed: ${e.message}")
        }
        return ""
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
