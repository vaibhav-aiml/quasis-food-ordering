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
 * Executes a single atomic OrderStep against Swiggy's window.
 *
 * Key design: after every action (typing text, firing intent, tapping coordinates),
 * we check if the TARGET RESULT is visible on screen. This decouples "how we searched"
 * from "did the search work".
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
    }

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

    // ================== STEP 1: LAUNCH ==================

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
            return ok(step, ScreenType.UNKNOWN, "Launched package: $packageName")
        }

        return fail(step, ScreenType.UNKNOWN, "Could not launch $packageName")
    }

    // ================== STEP 2: SEARCH RESTAURANT ==================

    private fun executeSearch(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Search query missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG)
        Log.d(TAG, "Search phase=$searchPhase, rootPkg=${swiggyRoot?.packageName}")

        if (swiggyRoot == null) {
            return fail(step, screen, "Waiting for Swiggy to load...")
        }

        // ============================================================
        // FIRST CHECK: Is the search result already visible on screen?
        // If "Domino's" text already appears, search is DONE regardless
        // of whether we typed it or URL intent loaded it.
        // ============================================================
        if (isTargetVisibleOnScreen(swiggyRoot, query)) {
            Log.i(TAG, "Target '$query' already visible on screen — search complete!")
            searchPhase = 0
            return ok(step, screen, "Search results showing for '$query'")
        }

        // === Phase 0: Try text injection into any editable field ===
        val typed = tryInjectText(swiggyRoot, query)
        if (typed) {
            searchPhase = 0
            return ok(step, screen, "Searched for '$query'")
        }

        // === Phase 1: Tap search-related UI elements ===
        if (searchPhase == 0) {
            val searchNodes = findAllSearchNodes(swiggyRoot)
            Log.d(TAG, "Phase 1: Found ${searchNodes.size} search nodes")
            for (node in searchNodes) {
                GestureDispatcher.clickNode(node, service)
            }
            searchPhase = 1
            return fail(step, screen, "Tapping search elements...")
        }

        // === Phase 2: Coordinate taps at various positions ===
        if (searchPhase == 1) {
            val dm = service.resources.displayMetrics
            val centerX = dm.widthPixels / 2f
            for (fraction in listOf(0.08f, 0.10f, 0.12f, 0.15f, 0.18f)) {
                GestureDispatcher.clickAtCoordinates(service, centerX, dm.heightPixels * fraction)
            }
            searchPhase = 2
            return fail(step, screen, "Tapping search coordinates...")
        }

        // === Phase 3: URL search intent ===
        if (searchPhase == 2) {
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
            return fail(step, screen, "Trying URL search for '$query'...")
        }

        // === Phase 4+: Re-check visibility each retry ===
        searchPhase++
        return fail(step, screen, "Waiting for '$query' results...")
    }

    // ================== STEP 3: SELECT RESTAURANT ==================

    private fun executeSelectRestaurant(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        // Find the restaurant name on screen
        val targetNode = findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            // Walk up to find a clickable ancestor (the card container)
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            val clicked = GestureDispatcher.clickNode(clickable, service)
            if (clicked) {
                return ok(step, screen, "Selected restaurant '$target'")
            }
        }

        // Try tapping suggestions / first clickable card
        val allVisible = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot)
        Log.d(TAG, "Visible texts: ${allVisible.take(10)}")

        // Scroll to find more content
        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for '$target' restaurant...")
    }

    // ================== STEP 4: SEARCH MENU ITEM ==================

    private fun executeSearchMenuItem(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val itemName = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        // Check if item is already visible
        if (isTargetVisibleOnScreen(swiggyRoot, itemName)) {
            return ok(step, screen, "Found '$itemName' on menu")
        }

        // Try in-menu search if available
        val menuSearchNodes = findAllSearchNodes(swiggyRoot)
        if (menuSearchNodes.isNotEmpty()) {
            val searchNode = menuSearchNodes.first()
            GestureDispatcher.clickNode(searchNode, service)
            // Try typing
            val typed = tryInjectText(service.getAppRoot(SWIGGY_PKG) ?: swiggyRoot, itemName)
            if (typed) return ok(step, screen, "Searched menu for '$itemName'")
        }

        // Scroll down to find the item
        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Scrolling to find '$itemName'...")
    }

    // ================== STEP 5: SELECT ITEM ==================

    private fun executeSelectItem(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        val targetNode = findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            if (GestureDispatcher.clickNode(clickable, service)) {
                return ok(step, screen, "Selected item '$target'")
            }
        }

        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for '$target'...")
    }

    // ================== STEP 6: ADD TO CART ==================

    private fun executeAddToCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: ""
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        // Check for customization dialogs first
        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "apply", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            return ok(step, screen, "Confirmed item addition")
        }

        // Look for ADD button
        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true)

        if (addButtons.isNotEmpty()) {
            val btn = addButtons.firstOrNull { it.isClickable } ?: addButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return if (clicked) ok(step, screen, "Tapped ADD for $target") else fail(step, screen, "Click failed")
        }

        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for ADD button...")
    }

    // ================== STEP 7: VIEW CART ==================

    private fun executeViewCart(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        val cartButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "view cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "checkout", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "review order", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "item added", exactMatch = false)

        if (cartButtons.isNotEmpty()) {
            val btn = cartButtons.firstOrNull { it.isClickable } ?: cartButtons.first()
            GestureDispatcher.clickNode(btn, service)
            return ok(step, screen, "Navigated to Cart")
        }

        return fail(step, screen, "Looking for Cart...")
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

    /**
     * Checks if the target text is already visible anywhere on Swiggy's screen.
     * This is the KEY fix — we detect success by RESULT, not by method.
     */
    private fun isTargetVisibleOnScreen(root: AccessibilityNodeInfo, query: String): Boolean {
        val cleanQuery = query.lowercase().replace("'", "").replace("\u2019", "")
        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(root)

        for (text in allTexts) {
            val cleanText = text.lowercase().replace("'", "").replace("\u2019", "")
            if (cleanText.contains(cleanQuery) || cleanQuery.contains(cleanText)) {
                // Make sure it's not just the search bar showing our typed text
                // Check if there are multiple matches (results list)
                val matches = NodeHierarchyScanner.findNodesByText(root, query, exactMatch = false)
                if (matches.size >= 1) {
                    // Verify at least one match is NOT an editable field (i.e., it's a result)
                    val nonEditableMatch = matches.any { node ->
                        val cls = node.className?.toString() ?: ""
                        !node.isEditable && !cls.contains("EditText", ignoreCase = true)
                    }
                    if (nonEditableMatch) return true
                }
            }
        }

        // Also check partial word matches (e.g., "Domino" matching "Domino's Pizza")
        val words = query.split(" ").filter { it.length >= 4 }
        for (word in words) {
            val wordMatches = NodeHierarchyScanner.findNodesByText(root, word, exactMatch = false)
            val nonEditableResults = wordMatches.filter { node ->
                val cls = node.className?.toString() ?: ""
                !node.isEditable && !cls.contains("EditText", ignoreCase = true)
            }
            if (nonEditableResults.size >= 1) return true
        }

        return false
    }

    /**
     * Try ALL text injection strategies.
     */
    private fun tryInjectText(root: AccessibilityNodeInfo, query: String): Boolean {
        // Strategy 1: Input-focused node
        val focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focusedNode != null) {
            if (GestureDispatcher.setText(service, focusedNode, query)) return true
        }

        // Strategy 2: Accessibility-focused editable node
        val a11yFocused = root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
        if (a11yFocused != null && a11yFocused.isEditable) {
            if (GestureDispatcher.setText(service, a11yFocused, query)) return true
        }

        // Strategy 3: Any node with ACTION_SET_TEXT
        val settableNodes = findNodesWithSetTextAction(root)
        for (node in settableNodes) {
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        // Strategy 4: Editable nodes by class name
        val editableNodes = findAllEditableNodes(root)
        for (node in editableNodes) {
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        return false
    }

    /**
     * Find the best matching node for a target text (restaurant name, dish name).
     * Tries exact match, then cleaned match, then word stems.
     */
    private fun findBestMatchingNode(root: AccessibilityNodeInfo, target: String): AccessibilityNodeInfo? {
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()

        // 1. Exact substring match
        var matches = NodeHierarchyScanner.findNodesByText(root, target, exactMatch = false)
        if (matches.isEmpty()) {
            matches = NodeHierarchyScanner.findNodesByText(root, cleanTarget, exactMatch = false)
        }

        // 2. Word stem matches
        if (matches.isEmpty()) {
            val words = target.split(" ").filter { it.length >= 4 }
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
     * Walk up the node tree to find the nearest clickable ancestor.
     * Critical for tapping restaurant cards where the text node itself isn't clickable.
     */
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

    // ================== NODE FINDERS ==================

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

    // ================== RESULT HELPERS ==================

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
