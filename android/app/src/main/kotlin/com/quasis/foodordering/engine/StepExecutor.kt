package com.quasis.foodordering.engine

import android.app.SearchManager
import android.content.Intent
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
 * Executes a single atomic OrderStep against the active window.
 * Uses Swiggy-specific window targeting to avoid reading our own app's tree.
 */
class StepExecutor(
    private val service: FoodAccessibilityService
) {
    companion object {
        private const val TAG = "StepExecutor"
        private const val SWIGGY_PKG = "in.swiggy.android"
    }

    /** Track search phase across retries */
    private var searchPhase = 0

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
            StepType.SELECT_RESTAURANT -> executeClickRestaurantOrDish(step, currentScreen)
            StepType.SEARCH_MENU_ITEM -> executeSearch(step, currentScreen)
            StepType.SELECT_ITEM -> executeClickRestaurantOrDish(step, currentScreen)
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
    }

    /**
     * Opens the Swiggy search screen once.
     */
    fun prepareSearchScreen() {
        try {
            val searchIntent = Intent(Intent.ACTION_VIEW, Uri.parse("swiggy://search")).apply {
                setPackage(SWIGGY_PKG)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            service.startActivity(searchIntent)
            Log.d(TAG, "Fired swiggy://search deep link")
        } catch (e: Exception) {
            Log.w(TAG, "Deep link failed", e)
        }
    }

    // ================== LAUNCH ==================

    private fun executeLaunchApp(step: OrderStepDto): StepExecutionResultDto {
        val packageName = step.parameters["package_name"]?.toString()
            ?.removeSurrounding("\"") ?: SWIGGY_PKG

        var launchIntent = service.packageManager.getLaunchIntentForPackage(packageName)
        if (launchIntent == null) {
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
        }

        if (launchIntent != null) {
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            service.startActivity(launchIntent)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                message = "Launched package: $packageName"
            )
        }

        return fail(step, ScreenType.UNKNOWN, "Could not launch $packageName")
    }

    // ================== SEARCH ==================

    private fun executeSearch(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Search query missing.")

        // CRITICAL: Get Swiggy's window root, not our app's
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)
        val activeRootPkg = swiggyRoot?.packageName?.toString() ?: "null"
        Log.d(TAG, "Search phase=$searchPhase, swiggyRoot pkg=$activeRootPkg")

        if (swiggyRoot == null || activeRootPkg != SWIGGY_PKG) {
            Log.w(TAG, "Swiggy window not found. Active pkg=$activeRootPkg")
            return fail(step, screen, "Waiting for Swiggy to load...")
        }

        // === Phase 0: Try to find and type into any editable field ===
        val typed = tryInjectText(swiggyRoot, query)
        if (typed) {
            Log.i(TAG, "Successfully typed '$query' into search")
            searchPhase = 0
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                observed_screen = screen.name,
                message = "Searched for '$query'"
            )
        }

        // === Phase 1: Tap on search elements to activate keyboard ===
        if (searchPhase == 0) {
            Log.d(TAG, "Phase 0 failed. Tapping search elements...")

            // Try clicking any node with "search" in text/description/id
            val searchNodes = findAllSearchNodes(swiggyRoot)
            Log.d(TAG, "Found ${searchNodes.size} search-related nodes")
            for (node in searchNodes) {
                GestureDispatcher.clickNode(node, service)
                Log.d(TAG, "  Clicked: class=${node.className} text=${node.text?.toString()?.take(30)}")
            }

            searchPhase = 1
            return fail(step, screen, "Tapped search elements, waiting for input...")
        }

        // === Phase 2: Coordinate-based taps at multiple Y positions ===
        if (searchPhase == 1) {
            Log.d(TAG, "Phase 1 failed. Tapping coordinates...")
            val dm = service.resources.displayMetrics
            val centerX = dm.widthPixels / 2f
            // Tap at 8%, 10%, 12%, 15%, 18% from top
            for (fraction in listOf(0.08f, 0.10f, 0.12f, 0.15f, 0.18f)) {
                val y = dm.heightPixels * fraction
                GestureDispatcher.clickAtCoordinates(service, centerX, y)
            }
            searchPhase = 2
            return fail(step, screen, "Tapped search bar coordinates...")
        }

        // === Phase 3: Try URL-based search as last resort ===
        if (searchPhase == 2) {
            Log.d(TAG, "Phase 2 failed. Trying URL-based search...")
            try {
                val encodedQuery = Uri.encode(query)
                val urlIntent = Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://www.swiggy.com/search?query=$encodedQuery")
                ).apply {
                    setPackage(SWIGGY_PKG)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                service.startActivity(urlIntent)
                Log.d(TAG, "Fired Swiggy URL search intent")
            } catch (e1: Exception) {
                try {
                    val searchIntent = Intent(Intent.ACTION_SEARCH).apply {
                        putExtra(SearchManager.QUERY, query)
                        setPackage(SWIGGY_PKG)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    service.startActivity(searchIntent)
                    Log.d(TAG, "Fired ACTION_SEARCH intent")
                } catch (e2: Exception) {
                    Log.w(TAG, "All search intents failed", e2)
                }
            }
            searchPhase = 3
            return fail(step, screen, "Tried URL search for '$query'...")
        }

        // === Phase 4+: Keep retrying text injection ===
        Log.d(TAG, "Phase 3+ - retrying text injection...")
        logNodeTree(swiggyRoot, 0)
        searchPhase++
        return fail(step, screen, "Retrying search input for '$query'...")
    }

    /**
     * Try ALL text injection strategies on the given root.
     */
    private fun tryInjectText(root: AccessibilityNodeInfo, query: String): Boolean {
        // Strategy 1: Input-focused node
        val focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focusedNode != null) {
            Log.d(TAG, "Found FOCUS_INPUT: class=${focusedNode.className} editable=${focusedNode.isEditable}")
            if (GestureDispatcher.setText(service, focusedNode, query)) return true
        }

        // Strategy 2: Accessibility-focused node
        val a11yFocused = root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
        if (a11yFocused != null && a11yFocused.isEditable) {
            Log.d(TAG, "Found A11Y_FOCUS editable: class=${a11yFocused.className}")
            if (GestureDispatcher.setText(service, a11yFocused, query)) return true
        }

        // Strategy 3: Nodes with ACTION_SET_TEXT
        val settableNodes = findNodesWithSetTextAction(root)
        Log.d(TAG, "Found ${settableNodes.size} ACTION_SET_TEXT nodes")
        for (node in settableNodes) {
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        // Strategy 4: Editable nodes by class/property
        val editableNodes = findAllEditableNodes(root)
        Log.d(TAG, "Found ${editableNodes.size} editable nodes")
        for (node in editableNodes) {
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        return false
    }

    // ================== SELECT RESTAURANT / DISH ==================

    private fun executeClickRestaurantOrDish(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target value missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()

        var matchingNodes = NodeHierarchyScanner.findNodesByText(swiggyRoot, target, exactMatch = false)
        if (matchingNodes.isEmpty()) {
            matchingNodes = NodeHierarchyScanner.findNodesByText(swiggyRoot, cleanTarget, exactMatch = false)
        }

        if (matchingNodes.isEmpty()) {
            val words = target.split(" ").filter { it.length >= 4 }
            for (w in words) {
                val matches = NodeHierarchyScanner.findNodesByText(swiggyRoot, w, exactMatch = false)
                if (matches.isNotEmpty()) {
                    matchingNodes = matches
                    break
                }
            }
        }

        if (matchingNodes.isNotEmpty()) {
            val nodeToClick = matchingNodes.firstOrNull { it.isClickable } ?: matchingNodes.first()
            if (GestureDispatcher.clickNode(nodeToClick, service)) {
                return StepExecutionResultDto(
                    step_id = step.step_id, step_type = step.step_type, success = true,
                    observed_screen = screen.name, message = "Selected '$target'"
                )
            }
        }

        // Fallback: first clickable result
        val resultCards = NodeHierarchyScanner.findNodesByText(swiggyRoot, "restaurant", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "dish", exactMatch = false)
        val card = resultCards.firstOrNull { it.isClickable }
        if (card != null && GestureDispatcher.clickNode(card, service)) {
            return StepExecutionResultDto(
                step_id = step.step_id, step_type = step.step_type, success = true,
                observed_screen = screen.name, message = "Selected first result for '$target'"
            )
        }

        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Locating '$target'...")
    }

    // ================== ADD TO CART ==================

    private fun executeAddToCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: ""
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)

        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "apply", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id, step_type = step.step_type, success = clicked,
                observed_screen = screen.name, message = "Confirmed item on customization sheet."
            )
        }

        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true)

        if (addButtons.isNotEmpty()) {
            val btn = addButtons.firstOrNull { it.isClickable } ?: addButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id, step_type = step.step_type, success = clicked,
                observed_screen = screen.name, message = if (clicked) "Tapped 'ADD' for $target" else "Failed"
            )
        }

        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for 'ADD' button...")
    }

    // ================== VIEW CART ==================

    private fun executeViewCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)
        val cartButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "view cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "checkout", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "review order", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "item added", exactMatch = false)

        if (cartButtons.isNotEmpty()) {
            val btn = cartButtons.firstOrNull { it.isClickable } ?: cartButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id, step_type = step.step_type, success = clicked,
                observed_screen = screen.name, message = "Navigated to Cart"
            )
        }

        return fail(step, screen, "Looking for Cart bar...")
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

        return StepExecutionResultDto(
            step_id = step.step_id, step_type = step.step_type, success = true,
            observed_screen = screen.name, message = "Processed customizations"
        )
    }

    // ================== HELPERS ==================

    private fun findAllSearchNodes(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val text = node.text?.toString()?.lowercase() ?: ""
            val desc = node.contentDescription?.toString()?.lowercase() ?: ""
            val viewId = node.viewIdResourceName?.lowercase() ?: ""
            val cls = node.className?.toString()?.lowercase() ?: ""

            if (text.contains("search") || desc.contains("search") ||
                viewId.contains("search") || cls.contains("search")) {
                results.add(node)
            }

            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
        }

        traverse(root)
        return results
    }

    private fun findNodesWithSetTextAction(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val actions = node.actionList
            if (actions != null && actions.any { it.id == AccessibilityNodeInfo.ACTION_SET_TEXT }) {
                results.add(node)
            }
            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
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
            if (node.isEditable ||
                cls.contains("EditText", ignoreCase = true) ||
                cls.contains("AutoComplete", ignoreCase = true) ||
                cls.contains("SearchView", ignoreCase = true) ||
                cls.contains("TextField", ignoreCase = true) ||
                cls.contains("TextInput", ignoreCase = true) ||
                cls.contains("Input", ignoreCase = true)) {
                results.add(node)
            }
            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
        }

        traverse(root)
        return results
    }

    private fun logNodeTree(node: AccessibilityNodeInfo?, depth: Int) {
        if (node == null || depth > 2) return
        val indent = "  ".repeat(depth)
        val cls = node.className?.toString()?.substringAfterLast('.') ?: "?"
        val text = node.text?.toString()?.take(25) ?: ""
        val desc = node.contentDescription?.toString()?.take(25) ?: ""
        val pkg = node.packageName?.toString() ?: ""
        val editable = if (node.isEditable) " EDIT" else ""
        val focused = if (node.isFocused) " FOCUS" else ""
        val clickable = if (node.isClickable) " CLICK" else ""
        val actionCount = node.actionList?.size ?: 0
        Log.d(TAG, "${indent}[$cls] pkg=$pkg txt='$text' desc='$desc'$editable$focused$clickable acts=$actionCount")
        for (i in 0 until node.childCount) {
            logNodeTree(node.getChild(i), depth + 1)
        }
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
