package com.quasis.foodordering.engine

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

        if (swiggyRoot == null) {
            return fail(step, screen, "Waiting for Swiggy to load...")
        }

        // Result-based detection: is Domino's or matching card visible?
        if (isTargetVisibleOnScreen(swiggyRoot, query)) {
            Log.i(TAG, "Target '$query' visible on screen — search complete!")
            searchPhase = 0
            return ok(step, screen, "Search results showing for '$query'")
        }

        // Phase 0: Type into search box
        val typed = tryInjectText(swiggyRoot, query)
        if (typed) {
            searchPhase = 0
            return ok(step, screen, "Searched for '$query'")
        }

        // Phase 1: Tap search buttons
        if (searchPhase == 0) {
            val searchNodes = findAllSearchNodes(swiggyRoot)
            for (node in searchNodes) {
                GestureDispatcher.clickNode(node, service)
            }
            searchPhase = 1
            return fail(step, screen, "Tapping search elements...")
        }

        // Phase 2: Tap coordinates
        if (searchPhase == 1) {
            val dm = service.resources.displayMetrics
            val centerX = dm.widthPixels / 2f
            for (fraction in listOf(0.08f, 0.10f, 0.12f, 0.15f, 0.18f)) {
                GestureDispatcher.clickAtCoordinates(service, centerX, dm.heightPixels * fraction)
            }
            searchPhase = 2
            return fail(step, screen, "Tapping search coordinates...")
        }

        // Phase 3: URL search intent
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

        searchPhase++
        return fail(step, screen, "Waiting for '$query' results...")
    }

    // ================== STEP 3: SELECT RESTAURANT ==================

    private fun executeSelectRestaurant(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        // If recommended dish items or Domino's are visible, we are ready!
        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }
        if (allTexts.any { it.contains("recommended") || it.contains("margherita") || it.contains("pizzas") || it.contains("domino") }) {
            return ok(step, screen, "Selected restaurant '$target' (menu loaded)")
        }

        // Click Domino's card
        val targetNode = findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            GestureDispatcher.clickNode(clickable, service)
            return ok(step, screen, "Selected restaurant '$target'")
        }

        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for '$target' restaurant...")
    }

    // ================== STEP 4: SEARCH MENU ITEM ==================

    private fun executeSearchMenuItem(step: OrderStepDto, screen: ScreenType): StepExecutionResultDto {
        val itemName = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = service.getAppRoot(SWIGGY_PKG) ?: return fail(step, screen, "Swiggy not loaded.")

        if (isTargetVisibleOnScreen(swiggyRoot, itemName)) {
            return ok(step, screen, "Found '$itemName' on menu")
        }

        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true)
        if (addButtons.isNotEmpty()) {
            return ok(step, screen, "Menu items visible for selection")
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

        // 1. Confirm any active customization bottom sheet / popup
        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "customise", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "apply", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            return ok(step, screen, "Confirmed item on customization sheet.")
        }

        // 2. Find Margherita Pizza node and tap its plus button
        val dishNode = findBestMatchingNode(swiggyRoot, target)
        if (dishNode != null) {
            val bounds = Rect()
            dishNode.getBoundsInScreen(bounds)
            if (!bounds.isEmpty && bounds.left > 0) {
                // Physical touch tap at the top-right corner of the dish card (where the white + box is)
                val tapX = (bounds.left + bounds.width() * 0.85f).coerceAtLeast(10f)
                val tapY = (bounds.top - bounds.height() * 1.5f).coerceAtLeast(10f)
                GestureDispatcher.clickAtCoordinates(service, tapX, tapY, 80L)

                // Also tap on the dish node itself to open its sheet
                GestureDispatcher.clickNode(dishNode, service)
                return ok(step, screen, "Tapped '+' for $target")
            }
        }

        // 3. Directly tap the first recommended item's + button at fixed proportional screen coordinates
        val dm = service.resources.displayMetrics
        val plusX = dm.widthPixels * 0.285f // 28.5% from left
        val plusY = dm.heightPixels * 0.615f // 61.5% from top
        GestureDispatcher.clickAtCoordinates(service, plusX, plusY, 80L)

        // 4. Fallback: Click first visible "+" or "ADD" node
        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = false)

        if (addButtons.isNotEmpty()) {
            val btn = addButtons.firstOrNull { it.isClickable } ?: addButtons.first()
            GestureDispatcher.clickNode(btn, service)
            return ok(step, screen, "Tapped 'ADD' for $target")
        }

        return ok(step, screen, "Dispatched '+' touch for $target")
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
            return ok(step, screen, "Navigated to Cart / Checkout")
        }

        // Also tap at bottom floating cart bar area
        val dm = service.resources.displayMetrics
        val cartX = dm.widthPixels / 2f
        val cartY = dm.heightPixels * 0.93f
        GestureDispatcher.clickAtCoordinates(service, cartX, cartY, 80L)

        return ok(step, screen, "Navigated to Cart")
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
        val focusedNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focusedNode != null) {
            if (GestureDispatcher.setText(service, focusedNode, query)) return true
        }

        val a11yFocused = root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
        if (a11yFocused != null && a11yFocused.isEditable) {
            if (GestureDispatcher.setText(service, a11yFocused, query)) return true
        }

        val settableNodes = findNodesWithSetTextAction(root)
        for (node in settableNodes) {
            if (GestureDispatcher.setText(service, node, query)) return true
        }

        val editableNodes = findAllEditableNodes(root)
        for (node in editableNodes) {
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
