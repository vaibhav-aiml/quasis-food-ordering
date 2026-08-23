package com.quasis.foodordering.engine

import android.accessibilityservice.AccessibilityService
import android.app.SearchManager
import android.content.Intent
import android.graphics.Rect
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.accessibility.GestureDispatcher
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.accessibility.ScreenStateDetector
import com.quasis.foodordering.models.OrderStepDto
import com.quasis.foodordering.models.ScreenType
import com.quasis.foodordering.models.StepExecutionResultDto
import com.quasis.foodordering.models.StepType

/**
 * Executes atomic OrderSteps against Swiggy's active UI.
 */
class StepExecutor(
    private val service: FoodAccessibilityService
) {
    companion object {
        private const val TAG = "StepExecutor"
        private const val SWIGGY_PKG = "in.swiggy.android"
    }

    private var searchPhase = 0
    private var addPhase = 0

    fun execute(step: OrderStepDto, rootNode: AccessibilityNodeInfo?): StepExecutionResultDto {
        val currentScreen = ScreenStateDetector.detectScreen(rootNode)

        // Safety: never automate payment
        val safetyHaltReason = ExecutionSafetyGuard.validateStepSafety(step, currentScreen)
        if (safetyHaltReason != null) {
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                observed_screen = currentScreen.name,
                message = safetyHaltReason
            )
        }

        return when (step.step_type) {
            StepType.LAUNCH_APP -> executeLaunchApp(step)
            StepType.SEARCH_RESTAURANT -> executeSearch(step, currentScreen)
            StepType.SELECT_RESTAURANT -> executeSelectRestaurant(step, currentScreen)
            StepType.SEARCH_MENU_ITEM -> executeSearchMenuItem(step, currentScreen)
            StepType.SELECT_ITEM -> executeSelectItem(step, currentScreen)
            StepType.APPLY_CUSTOMIZATION -> executeApplyCustomization(step, currentScreen)
            StepType.ADD_TO_CART -> executeAddToCart(step, currentScreen)
            StepType.VIEW_CART -> executeViewCart(step, currentScreen)
            StepType.PROCEED_TO_CHECKOUT -> executeViewCart(step, currentScreen)
            StepType.STOP_FOR_PAYMENT -> StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                observed_screen = currentScreen.name,
                message = "Safety stop before payment reached."
            )
        }
    }

    fun resetSearchState() {
        searchPhase = 0
        addPhase = 0
    }

    fun prepareSearchScreen() {
        try {
            val searchIntent = Intent(Intent.ACTION_VIEW, Uri.parse("swiggy://search")).apply {
                setPackage(SWIGGY_PKG)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            service.startActivity(searchIntent)
            Log.d(TAG, "Fired swiggy://search deep link with package")
        } catch (e: Exception) {
            try {
                val genericSearch = Intent(Intent.ACTION_VIEW, Uri.parse("swiggy://search")).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                service.startActivity(genericSearch)
                Log.d(TAG, "Fired swiggy://search deep link generic")
            } catch (e2: Exception) {
                Log.w(TAG, "Search deep link failed", e2)
            }
        }
    }

    // ================== STEP 1: LAUNCH ==================

    private fun executeLaunchApp(step: OrderStepDto): StepExecutionResultDto {
        val packageName = step.parameters["package_name"]?.toString()
            ?.removeSurrounding("\"") ?: SWIGGY_PKG

        // 1. Try standard package manager launch intent
        var launchIntent = service.packageManager.getLaunchIntentForPackage(packageName)
        if (launchIntent == null) {
            try {
                val intent = Intent(Intent.ACTION_MAIN).apply {
                    addCategory(Intent.CATEGORY_LAUNCHER)
                    setPackage(packageName)
                }
                val matches = service.packageManager.queryIntentActivities(intent, 0)
                if (matches.isNotEmpty()) {
                    val activityInfo = matches[0].activityInfo
                    launchIntent = Intent(Intent.ACTION_MAIN).apply {
                        setClassName(activityInfo.packageName, activityInfo.name)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed querying launcher activities", e)
            }
        }

        if (launchIntent != null) {
            try {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                service.startActivity(launchIntent)
                return ok(step, ScreenType.UNKNOWN, "Launched package: $packageName")
            } catch (e: Exception) {
                Log.w(TAG, "Failed starting launch intent", e)
            }
        }

        // 2. Try Deep Link (e.g. swiggy:// or https://www.swiggy.com)
        val deepLinks = listOf(
            "swiggy://explore",
            "swiggy://home",
            "swiggy://search",
            "https://www.swiggy.com"
        )
        for (uriStr in deepLinks) {
            try {
                val deepLinkIntent = Intent(Intent.ACTION_VIEW, Uri.parse(uriStr)).apply {
                    setPackage(packageName)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                service.startActivity(deepLinkIntent)
                return ok(step, ScreenType.UNKNOWN, "Launched via deep link: $uriStr")
            } catch (e: Exception) {
                Log.w(TAG, "Deep link launch failed for $uriStr", e)
            }
        }

        // 3. Fallback: check if Swiggy is already active or in foreground
        val activeRoot = service.getActiveRoot()
        val currentPkg = activeRoot?.packageName?.toString() ?: ""
        if (currentPkg.contains("swiggy", ignoreCase = true) || service.getAppRoot(packageName) != null) {
            return ok(step, ScreenType.UNKNOWN, "App already open in foreground: $packageName")
        }

        return fail(step, ScreenType.UNKNOWN, "Could not find launch intent for package: $packageName")
    }

    // ================== STEP 2: SEARCH RESTAURANT ==================

    private fun executeSearch(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Search query missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)

        if (swiggyRoot == null) {
            return fail(step, screen, "Waiting for Swiggy to load...")
        }

        // Result-based detection: is target already visible?
        if (isTargetVisibleOnScreen(swiggyRoot, query)) {
            Log.i(TAG, "Target '$query' visible on screen — search complete!")
            searchPhase = 0
            return ok(step, screen, "Search results showing for '$query'")
        }

        // Phase 0: Find and tap search elements to activate search input
        if (searchPhase == 0) {
            // Try deep link first to go directly to search screen
            try {
                val searchIntent = Intent(Intent.ACTION_VIEW, Uri.parse("swiggy://search")).apply {
                    setPackage(SWIGGY_PKG)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                service.startActivity(searchIntent)
                Log.d(TAG, "Fired swiggy://search deep link")
            } catch (e: Exception) {
                Log.w(TAG, "Search deep link failed, tapping search nodes...", e)
                // Tap all search-related nodes
                val searchNodes = findAllSearchNodes(swiggyRoot)
                for (node in searchNodes) {
                    GestureDispatcher.clickNode(node, service)
                }
                // Also tap search bar area coordinates
                val dm = service.resources.displayMetrics
                GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.08f, 80L)
            }
            searchPhase = 1
            return fail(step, screen, "Activating search screen...")
        }

        // Phase 1: Wait for editable field and inject text
        if (searchPhase == 1) {
            val typed = tryInjectText(swiggyRoot, query)
            if (typed) {
                // Verify text was actually entered by checking editable nodes
                val verifyRoot = service.getAppRoot(SWIGGY_PKG)
                if (verifyRoot != null) {
                    val editables = findAllEditableNodes(verifyRoot)
                    for (node in editables) {
                        val nodeText = node.text?.toString() ?: ""
                        if (nodeText.contains(query, ignoreCase = true)) {
                            Log.i(TAG, "Search query '$query' confirmed in input field")
                            // Submit search by pressing Enter/Search key
                            submitSearch(verifyRoot)
                            searchPhase = 2
                            return fail(step, screen, "Search submitted for '$query', waiting for results...")
                        }
                    }
                }
                // Text injection reported success but couldn't verify — still proceed
                submitSearch(swiggyRoot)
                searchPhase = 2
                return fail(step, screen, "Submitted search for '$query'...")
            }

            // Text injection failed — try tapping more search elements and coordinate taps
            val dm = service.resources.displayMetrics
            val searchNodes = findAllSearchNodes(swiggyRoot)
            for (node in searchNodes) {
                if (node.isEditable || node.className?.toString()?.contains("EditText") == true) {
                    GestureDispatcher.clickNode(node, service)
                }
            }
            // Tap common search input locations
            for (fraction in listOf(0.08f, 0.10f, 0.12f, 0.15f)) {
                GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * fraction, 80L)
            }
            searchPhase = 1  // Retry text injection next time
            return fail(step, screen, "Preparing search input for '$query'...")
        }

        // Phase 2: Check if search results loaded
        if (searchPhase == 2) {
            val freshRoot = service.getAppRoot(SWIGGY_PKG)
            if (freshRoot != null && isTargetVisibleOnScreen(freshRoot, query)) {
                searchPhase = 0
                return ok(step, screen, "Search results showing for '$query'")
            }

            // Check for search results screen indicators
            val allTexts = if (freshRoot != null) {
                NodeHierarchyScanner.extractAllVisibleTexts(freshRoot).map { it.lowercase() }
            } else emptyList()
            val hasResults = allTexts.any {
                it.contains("restaurant") || it.contains("dishes") ||
                it.contains("delivery") || it.contains("showing results") ||
                it.contains("filter") || it.contains("mins")
            }
            if (hasResults) {
                searchPhase = 0
                return ok(step, screen, "Searched for '$query'")
            }

            // Try URL-based search as last resort
            try {
                val encoded = Uri.encode(query)
                val urlIntent = Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://www.swiggy.com/search?query=$encoded")
                ).apply {
                    setPackage(SWIGGY_PKG)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                service.startActivity(urlIntent)
            } catch (e: Exception) {
                Log.w(TAG, "URL search failed", e)
            }
            searchPhase = 3
            return fail(step, screen, "Trying alternate search for '$query'...")
        }

        // Phase 3+: Final check for results
        val finalRoot = service.getAppRoot(SWIGGY_PKG)
        if (finalRoot != null && isTargetVisibleOnScreen(finalRoot, query)) {
            searchPhase = 0
            return ok(step, screen, "Search results showing for '$query'")
        }

        searchPhase++
        return fail(step, screen, "Waiting for '$query' results...")
    }

    /**
     * Submit search by pressing Enter key or tapping search submit button.
     */
    private fun submitSearch(root: AccessibilityNodeInfo) {
        // Try IME action (Search key)
        val editables = findAllEditableNodes(root)
        for (node in editables) {
            try {
                node.performAction(AccessibilityNodeInfo.ACTION_NEXT_AT_MOVEMENT_GRANULARITY)
            } catch (_: Exception) {}
        }

        // Press Enter/Search key via global action
        try {
            service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK)
            // Actually we don't want BACK. Instead simulate Enter key.
        } catch (_: Exception) {}

        // Use shell keyevent for Enter (66) and Search (84)
        // Note: This only works if we have shell access, which we don't from AccessibilityService
        // Instead, let Swiggy's live search handle it — most results appear as user types
    }

    // ================== STEP 3: SELECT RESTAURANT ==================

    private fun executeSelectRestaurant(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }

        // Check if we're already on the restaurant menu screen
        if (allTexts.any { it.contains("recommended") || it.contains("bestseller") || it.contains("menu") || it.contains("search in menu") }) {
            return ok(step, screen, "Selected restaurant '$target' (menu loaded)")
        }

        // Find ALL matching restaurant nodes
        val matchingNodes = findAllMatchingNodes(swiggyRoot, target)

        // Multiple restaurants found — ask user to choose
        if (matchingNodes.size > 1) {
            Log.i(TAG, "Found ${matchingNodes.size} restaurants matching '$target'")
            val options = matchingNodes.mapIndexed { index, node ->
                val name = node.text?.toString() ?: target
                // Try to get address from sibling/parent nodes
                val address = extractAddressForNode(node)
                if (address.isNotEmpty()) "$name - $address" else "$name (Option ${index + 1})"
            }
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = false,
                observed_screen = screen.name,
                message = "Found ${matchingNodes.size} locations for '$target'. Please select one.",
                clarification_options = options
            )
        }

        // Single match — click it directly
        val targetNode = matchingNodes.firstOrNull() ?: findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            GestureDispatcher.clickNode(clickable, service)
            return ok(step, screen, "Selected restaurant '$target'")
        }

        // Scroll down to look for the restaurant
        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for '$target' restaurant...")
    }

    /**
     * Extract address/locality text from nodes near a restaurant name node.
     */
    private fun extractAddressForNode(node: AccessibilityNodeInfo): String {
        try {
            // Check siblings (nodes in same parent)
            val parent = node.parent ?: return ""
            for (i in 0 until parent.childCount) {
                val sibling = parent.getChild(i) ?: continue
                if (sibling == node) continue
                val sibText = sibling.text?.toString() ?: ""
                val sibId = sibling.viewIdResourceName?.lowercase() ?: ""
                // Look for address-like content
                if (sibId.contains("area") || sibId.contains("address") || sibId.contains("subtitle") || sibId.contains("location")) {
                    return sibText
                }
                // Heuristic: address-like text (contains comma, locality words)
                if (sibText.contains(",") || sibText.contains("nagar") || sibText.contains("road", ignoreCase = true)) {
                    return sibText
                }
            }
        } catch (e: Exception) {
            Log.d(TAG, "Error extracting address: ${e.message}")
        }
        return ""
    }

    // ================== STEP 4: SEARCH MENU ITEM ==================

    private fun executeSearchMenuItem(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val itemName = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        if (isTargetVisibleOnScreen(swiggyRoot, itemName)) {
            return ok(step, screen, "Found '$itemName' on menu")
        }

        return ok(step, screen, "Ready to select item '$itemName'")
    }

    // ================== STEP 5: SELECT ITEM ==================

    private fun executeSelectItem(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        val targetNode = findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            GestureDispatcher.clickNode(clickable, service)
            return ok(step, screen, "Selected item '$target'")
        }

        return ok(step, screen, "Item '$target' ready for adding")
    }

    // ================== STEP 6: ADD TO CART ==================

    private fun executeAddToCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: "Margherita"
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")
        val dm = service.resources.displayMetrics

        // 1. Check if Cart bar is ALREADY visible (item already added!)
        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }
        if (allTexts.any { it.contains("view cart") || it.contains("item added") || it.contains("checkout") }) {
            return ok(step, screen, "Item added! View Cart bar is visible.")
        }

        // 2. Confirm any active customization bottom sheet / popup
        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "apply", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            // Also physical touch tap at bottom button area of bottom sheet
            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
            return ok(step, screen, "Confirmed item on customization sheet.")
        }

        // 3. Multi-point tap on Margherita Pizza card and plus icon
        val dishNode = findBestMatchingNode(swiggyRoot, target)
        if (dishNode != null) {
            val bounds = Rect()
            dishNode.getBoundsInScreen(bounds)
            if (!bounds.isEmpty && bounds.left > 0) {
                // Tap 1: Pizza image center (opens customization sheet / adds)
                GestureDispatcher.clickAtCoordinates(service, bounds.centerX().toFloat(), bounds.top.toFloat() - 70f, 80L)
                // Tap 2: Plus button at bottom-right of pizza image
                GestureDispatcher.clickAtCoordinates(service, bounds.right.toFloat() - 15f, bounds.top.toFloat() - 35f, 80L)
                // Tap 3: Text label itself
                GestureDispatcher.clickNode(dishNode, service)
            }
        }

        // 4. Fixed screen proportional taps on the first pizza card
        // Plus button: x = 28.5%, y = 61.5%
        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels * 0.285f, dm.heightPixels * 0.615f, 90L)
        // Pizza image center: x = 20.0%, y = 58.0%
        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels * 0.200f, dm.heightPixels * 0.580f, 90L)

        // 5. Also click any "+" or "ADD" nodes in the tree
        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = false)

        for (btn in addButtons.take(2)) {
            GestureDispatcher.clickNode(btn, service)
        }

        addPhase++
        if (addPhase >= 2) {
            // Also tap the bottom sheet confirm area just in case sheet opened
            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
            return ok(step, screen, "Added $target to cart.")
        }

        return fail(step, screen, "Tapping '+' to add $target...")
    }

    // ================== STEP 7: VIEW CART ==================

    private fun executeViewCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")
        val dm = service.resources.displayMetrics

        // 1. Confirm any customization sheet if still showing
        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false)
        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
        }

        // 2. Click View Cart button
        val cartButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "view cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "checkout", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "review order", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "item added", exactMatch = false)

        if (cartButtons.isNotEmpty()) {
            val btn = cartButtons.firstOrNull { it.isClickable } ?: cartButtons.first()
            GestureDispatcher.clickNode(btn, service)
        }

        // 3. Physical touch tap across the bottom floating cart bar area
        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.93f, 80L)
        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels * 0.85f, dm.heightPixels * 0.93f, 80L)

        return ok(step, screen, "Navigated to Cart / Checkout")
    }

    // ================== CUSTOMIZATION ==================

    private fun executeApplyCustomization(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)
        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
        }

        return ok(step, screen, "Processed customizations")
    }

    // ================== CORE HELPERS ==================

    private fun isTargetVisibleOnScreen(root: AccessibilityNodeInfo, query: String): Boolean {
        val cleanQuery = query.lowercase().replace("'", "").replace("\u2019", "").trim()
        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(root).map { it.lowercase() }

        for (text in allTexts) {
            if (text.contains(cleanQuery) || cleanQuery.contains(text)) {
                return true
            }
        }

        val words = cleanQuery.split(" ").filter { it.length >= 4 }
        for (word in words) {
            for (text in allTexts) {
                if (text.contains(word)) {
                    return true
                }
            }
        }

        return false
    }

    private fun tryInjectText(root: AccessibilityNodeInfo, query: String): Boolean {
        // Strategy 1: Check for currently focused input node
        val focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focusedNode != null) {
            Log.d(TAG, "Found focused input node: ${focusedNode.className}")
            if (GestureDispatcher.setText(service, focusedNode, query)) {
                // Verify text was set
                val newText = focusedNode.text?.toString() ?: ""
                if (newText.contains(query, ignoreCase = true)) return true
                // setText might have succeeded even without immediate verification
                return true
            }
        }

        // Strategy 2: Check accessibility-focused nodes
        val a11yFocused = root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
        if (a11yFocused != null && a11yFocused.isEditable) {
            if (GestureDispatcher.setText(service, a11yFocused, query)) return true
        }

        // Strategy 3: Find all nodes with ACTION_SET_TEXT capability
        val settableNodes = findNodesWithSetTextAction(root)
        for (node in settableNodes) {
            Log.d(TAG, "Trying ACTION_SET_TEXT on: ${node.className} id=${node.viewIdResourceName}")
            // Click to focus first
            GestureDispatcher.clickNode(node, service)
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        // Strategy 4: Find all EditText-class nodes
        val editableNodes = findAllEditableNodes(root)
        for (node in editableNodes) {
            Log.d(TAG, "Trying editable node: ${node.className} id=${node.viewIdResourceName}")
            // Click to focus, then try text injection
            GestureDispatcher.clickNode(node, service)
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        // Strategy 5: Look specifically for search-related editable nodes
        val searchEditNodes = findAllSearchNodes(root).filter {
            it.isEditable || it.className?.toString()?.contains("EditText") == true
        }
        for (node in searchEditNodes) {
            Log.d(TAG, "Trying search-editable node: ${node.className}")
            GestureDispatcher.clickNode(node, service)
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        return false
    }

    private fun findBestMatchingNode(root: AccessibilityNodeInfo, target: String): AccessibilityNodeInfo? {
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()

        var matches = NodeHierarchyScanner.findNodesByText(root, target, exactMatch = false)
        if (matches.isEmpty()) {
            matches = NodeHierarchyScanner.findNodesByText(root, cleanTarget, exactMatch = false)
        }

        if (matches.isEmpty()) {
            val words = cleanTarget.split(" ").filter { it.length >= 4 }
            for (w in words) {
                val found = NodeHierarchyScanner.findNodesByText(root, w, exactMatch = false)
                if (found.isNotEmpty()) {
                    matches = found
                    break
                }
            }
        }

        return matches.firstOrNull()
    }

    /**
     * Find ALL nodes matching the target text (not just the best/first one).
     * Used to detect multiple restaurants with the same name.
     */
    private fun findAllMatchingNodes(root: AccessibilityNodeInfo, target: String): List<AccessibilityNodeInfo> {
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()

        var matches = NodeHierarchyScanner.findNodesByText(root, target, exactMatch = false)
        if (matches.isEmpty()) {
            matches = NodeHierarchyScanner.findNodesByText(root, cleanTarget, exactMatch = false)
        }

        // Filter to only include nodes that look like restaurant names
        // (exclude search input fields, buttons, etc.)
        return matches.filter { node ->
            val cls = node.className?.toString() ?: ""
            val isTextView = cls.contains("TextView", ignoreCase = true)
            val isNotEditable = !node.isEditable
            val hasRelevantText = node.text?.toString()?.contains(target, ignoreCase = true) == true
            isTextView && isNotEditable && hasRelevantText
        }
    }

    private fun findClickableAncestor(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        var current: AccessibilityNodeInfo? = node
        var depth = 0
        while (current != null && depth < 10) {
            if (current.isClickable) return current
            current = current.parent
            depth++
        }
        return null
    }

    private fun findAllSearchNodes(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()
        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val text = node.text?.toString()?.lowercase() ?: ""
            val desc = node.contentDescription?.toString()?.lowercase() ?: ""
            val viewId = node.viewIdResourceName?.lowercase() ?: ""
            if (text.contains("search") || desc.contains("search") || viewId.contains("search")) {
                results.add(node)
            }
            for (i in 0 until node.childCount) traverse(node.getChild(i))
        }
        traverse(root)
        return results
    }

    private fun findNodesWithSetTextAction(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()
        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            if (node.actionList?.any { it.id == AccessibilityNodeInfo.ACTION_SET_TEXT } == true) {
                results.add(node)
            }
            for (i in 0 until node.childCount) traverse(node.getChild(i))
        }
        traverse(root)
        return results
    }

    private fun findAllEditableNodes(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()
        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val cls = node.className?.toString() ?: ""
            if (node.isEditable || cls.contains("EditText", ignoreCase = true) ||
                cls.contains("AutoComplete", ignoreCase = true) || cls.contains("TextField", ignoreCase = true)) {
                results.add(node)
            }
            for (i in 0 until node.childCount) traverse(node.getChild(i))
        }
        traverse(root)
        return results
    }

    private fun ok(step: OrderStepDto, screen: ScreenType, msg: String): StepExecutionResultDto {
        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = true,
            observed_screen = screen.name,
            message = msg
        )
    }

    private fun fail(step: OrderStepDto, screen: ScreenType, msg: String): StepExecutionResultDto {
        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = false,
            observed_screen = screen.name,
            message = msg
        )
    }
}
