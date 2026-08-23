package com.quasis.foodordering.engine

import android.accessibilityservice.AccessibilityService
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
 * Executes atomic OrderSteps against Swiggy's active UI with multi-strategy fallbacks.
 */
class StepExecutor(
    private val service: FoodAccessibilityService
) {
    companion object {
        private const val TAG = "StepExecutor"
        private const val SWIGGY_PKG = "in.swiggy.android"
    }

    fun execute(step: OrderStepDto, rootNode: AccessibilityNodeInfo?): StepExecutionResultDto {
        val activeRoot = rootNode ?: service.getAppRoot(SWIGGY_PKG) ?: service.getActiveRoot()
        val currentScreen = ScreenStateDetector.detectScreen(activeRoot)

        // Dismiss common popups on screen first
        if (activeRoot != null) {
            dismissPopupsIfPresent(activeRoot)
        }

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
            StepType.SEARCH_RESTAURANT -> executeSearch(step, currentScreen, activeRoot)
            StepType.SELECT_RESTAURANT -> executeSelectRestaurant(step, currentScreen, activeRoot)
            StepType.SEARCH_MENU_ITEM -> executeSearchMenuItem(step, currentScreen, activeRoot)
            StepType.SELECT_ITEM -> executeSelectItem(step, currentScreen, activeRoot)
            StepType.APPLY_CUSTOMIZATION -> executeApplyCustomization(step, currentScreen, activeRoot)
            StepType.ADD_TO_CART -> executeAddToCart(step, currentScreen, activeRoot)
            StepType.VIEW_CART, StepType.PROCEED_TO_CHECKOUT -> executeViewCart(step, currentScreen, activeRoot)
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
        // Stateless execution
    }

    private fun resolveRoot(root: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        val rootPkg = root?.packageName?.toString() ?: ""
        if (root != null && !rootPkg.contains("foodordering") && !rootPkg.contains("permission")) {
            return root
        }
        val appRoot = service.getAppRoot(SWIGGY_PKG)
        if (appRoot != null) {
            val appPkg = appRoot.packageName?.toString() ?: ""
            if (!appPkg.contains("foodordering") && !appPkg.contains("permission")) {
                return appRoot
            }
        }
        val active = service.getActiveRoot()
        if (active != null) {
            val activePkg = active.packageName?.toString() ?: ""
            if (!activePkg.contains("foodordering") && !activePkg.contains("permission")) {
                return active
            }
        }
        return null
    }

    // ================== POPUP DISMISSAL ==================

    private fun dismissPopupsIfPresent(root: AccessibilityNodeInfo) {
        try {
            // 0. OS-level runtime permission dialogs (location, notifications) block Swiggy's
            // own window from ever becoming focused/rooted. Check by package and button texts.
            val rootPkg = root.packageName?.toString() ?: ""
            if (rootPkg.contains("permissioncontroller") || rootPkg.contains("permission")) {
                val allowTexts = listOf(
                    "while using the app", "only this time", "allow",
                    "allow all the time", "turn on"
                )
                for (txt in allowTexts) {
                    val nodes = NodeHierarchyScanner.findNodesByText(root, txt, exactMatch = false)
                    val target = nodes.firstOrNull { it.isClickable } ?: nodes.firstOrNull()
                    if (target != null) {
                        val clickable = findClickableAncestor(target) ?: target
                        clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        Log.d(TAG, "Granted OS permission dialog via '$txt'")
                        return
                    }
                }
                // Unknown permission dialog layout — deny rather than hang forever
                val denyNodes = NodeHierarchyScanner.findNodesByText(root, "deny", exactMatch = false) +
                        NodeHierarchyScanner.findNodesByText(root, "don't allow", exactMatch = false)
                val deny = denyNodes.firstOrNull { it.isClickable }
                if (deny != null) {
                    deny.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    Log.d(TAG, "Denied unrecognized permission dialog to unblock pipeline")
                    return
                }
            }

            val dismissTexts = listOf(
                "not now", "later", "cancel", "skip", "close", "✕", "dismiss",
                "maybe later", "remind me later", "no thanks", "got it", "ok"
            )
            for (txt in dismissTexts) {
                val nodes = NodeHierarchyScanner.findNodesByText(root, txt, exactMatch = true)
                for (n in nodes) {
                    val clickable = findClickableAncestor(n) ?: n
                    if (clickable.isClickable) {
                        clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        Log.d(TAG, "Dismissed popup via text '$txt'")
                        return
                    }
                }
            }

            val closeButtons = NodeHierarchyScanner.findNodesByResourceId(root, "in.swiggy.android:id/close_button") +
                    NodeHierarchyScanner.findNodesByResourceId(root, "in.swiggy.android:id/btn_close") +
                    NodeHierarchyScanner.findNodesByResourceId(root, "in.swiggy.android:id/iv_close") +
                    NodeHierarchyScanner.findNodesByResourceId(root, "in.swiggy.android:id/cross_icon")
            for (btn in closeButtons) {
                val clickable = findClickableAncestor(btn) ?: btn
                if (clickable.isClickable) {
                    clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    Log.d(TAG, "Dismissed popup via close button ID")
                    return
                }
            }
        } catch (e: Exception) {
            Log.d(TAG, "Popup check error: ${e.message}")
        }
    }

    // ================== STEP 1: LAUNCH ==================

    private fun executeLaunchApp(step: OrderStepDto): StepExecutionResultDto {
        val packageName = step.parameters["package_name"]?.toString()
            ?.removeSurrounding("\"") ?: SWIGGY_PKG

        val launchIntent = service.packageManager.getLaunchIntentForPackage(packageName)
        if (launchIntent != null) {
            try {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
                service.startActivity(launchIntent)
                return ok(step, ScreenType.UNKNOWN, "Launched package: $packageName")
            } catch (e: Exception) {
                Log.w(TAG, "Launch intent failed", e)
            }
        }

        val activeRoot = service.getActiveRoot()
        val currentPkg = activeRoot?.packageName?.toString() ?: ""
        if (currentPkg.contains("swiggy", ignoreCase = true) || service.getAppRoot(packageName) != null) {
            return ok(step, ScreenType.UNKNOWN, "App already open in foreground: $packageName")
        }

        return fail(step, ScreenType.UNKNOWN, "Could not find launch intent for package: $packageName")
    }

    // ================== STEP 2: SEARCH RESTAURANT ==================

    private fun executeSearch(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Search query missing.")
        val swiggyRoot = resolveRoot(root)

        if (swiggyRoot == null) {
            // Tap top search bar coordinates to wake up screen
            val dm = service.resources.displayMetrics
            val centerX = dm.widthPixels / 2f
            GestureDispatcher.clickAtCoordinates(service, centerX, dm.heightPixels * 0.08f, 80L)
            return fail(step, screen, "Waiting for Swiggy screen to load...")
        }

        if (isTargetVisibleOnScreen(swiggyRoot, query)) {
            Log.i(TAG, "Target '$query' visible on screen — search complete!")
            return ok(step, screen, "Search results showing for '$query'")
        }

        val editables = findAllEditableNodes(swiggyRoot)
        if (editables.isNotEmpty()) {
            val editNode = editables.first()
            val currentText = editNode.text?.toString() ?: ""

            if (currentText.contains(query, ignoreCase = true)) {
                val suggestions = findSearchSuggestions(swiggyRoot, query)
                if (suggestions.isNotEmpty()) {
                    val sug = suggestions.first()
                    val clickable = findClickableAncestor(sug) ?: sug
                    GestureDispatcher.clickNode(clickable, service)
                    Log.i(TAG, "Tapped suggestion for '$query'")
                    return ok(step, screen, "Selected search suggestion for '$query'")
                }

                val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }
                if (allTexts.any { it.contains("restaurant") || it.contains("dishes") || it.contains("mins") || it.contains("delivery") }) {
                    val restTabs = NodeHierarchyScanner.findNodesByText(swiggyRoot, "restaurants", exactMatch = true)
                    for (tab in restTabs) {
                        if (tab.isClickable) tab.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    }
                    return ok(step, screen, "Search results displayed for '$query'")
                }

                submitSearch(swiggyRoot)
                return ok(step, screen, "Searched for '$query'")
            } else {
                Log.d(TAG, "Injecting '$query' into search field...")
                val injected = GestureDispatcher.setText(service, editNode, query)
                if (injected) {
                    submitSearch(swiggyRoot)
                    return ok(step, screen, "Entered search query '$query'")
                }
            }
        }

        val searchBarNodes = findHomeSearchNodes(swiggyRoot)
        if (searchBarNodes.isNotEmpty()) {
            val targetBar = searchBarNodes.first()
            val clickable = findClickableAncestor(targetBar) ?: targetBar
            val clicked = GestureDispatcher.clickNode(clickable, service)
            Log.d(TAG, "Tapped search bar node (clicked=$clicked)")
            return fail(step, screen, "Tapping search bar to open search...")
        }

        // Relative targeting: if favourites carousel is on screen, search bar is directly above it
        val dm = service.resources.displayMetrics
        val centerX = dm.widthPixels / 2f
        val favNodes = NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "favourite_ryl_root_layout")
        var tapY = dm.heightPixels * 0.085f
        if (favNodes.isNotEmpty()) {
            var highestFav = dm.heightPixels
            for (f in favNodes) {
                val b = Rect()
                f.getBoundsInScreen(b)
                if (b.top in 10 until highestFav) highestFav = b.top
            }
            if (highestFav < dm.heightPixels && highestFav > 100) {
                tapY = (highestFav - 70).toFloat().coerceAtLeast(dm.heightPixels * 0.07f)
            }
        }

        GestureDispatcher.clickAtCoordinates(service, centerX, tapY, 80L)
        return fail(step, screen, "Opening search for '$query'...")
    }

    private fun findHomeSearchNodes(root: AccessibilityNodeInfo): List<AccessibilityNodeInfo> {
        val results = mutableListOf<AccessibilityNodeInfo>()
        val dm = service.resources.displayMetrics
        val screenHeight = dm.heightPixels

        val favNodes = NodeHierarchyScanner.findNodesByResourceId(root, "favourite_ryl_root_layout")
        var minFavTop = screenHeight
        for (fav in favNodes) {
            val b = Rect()
            fav.getBoundsInScreen(b)
            if (b.top in 10 until minFavTop) {
                minFavTop = b.top
            }
        }

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val id = node.viewIdResourceName?.lowercase() ?: ""
            val text = node.text?.toString()?.lowercase() ?: ""
            val desc = node.contentDescription?.toString()?.lowercase() ?: ""
            val cls = node.className?.toString() ?: ""

            // Exclude obvious non-search header elements
            val isExcluded = id.contains("profile") || id.contains("account") ||
                    id.contains("location") || id.contains("address") ||
                    id.contains("notification") || id.contains("bell") ||
                    id.contains("cart") || desc.contains("cart") ||
                    desc.contains("profile") || desc.contains("account")

            if (!isExcluded) {
                val isExplicitSearch = id.contains("search") ||
                        text.contains("search") ||
                        desc.contains("search") ||
                        text.contains("restaurant") ||
                        desc.contains("restaurant") ||
                        text.contains("groceries") ||
                        desc.contains("groceries") ||
                        text.contains("dish") ||
                        desc.contains("dish") ||
                        text.contains("biryani") ||
                        text.contains("pizza") ||
                        text.contains("burger") ||
                        text.contains("cake") ||
                        text.contains("mind")

                val bounds = Rect()
                node.getBoundsInScreen(bounds)

                if (isExplicitSearch && !node.isEditable && !cls.contains("EditText", ignoreCase = true)) {
                    results.add(node)
                }

                // Clickable container above favourites carousel in the top 25% of screen
                if (node.isClickable && bounds.height() > 30 && bounds.bottom <= minFavTop && bounds.top < screenHeight * 0.25f) {
                    if (isExplicitSearch || id.contains("query") || id.contains("bar") || id.contains("container") || bounds.width() > dm.widthPixels * 0.5f) {
                        results.add(node)
                    }
                }
            }

            for (i in 0 until node.childCount) traverse(node.getChild(i))
        }
        traverse(root)

        // Prioritize explicit search text, then wide clickable containers
        return results.distinct().sortedByDescending { n ->
            val txt = (n.text?.toString() ?: "") + " " + (n.contentDescription?.toString() ?: "")
            if (txt.contains("search", ignoreCase = true)) 3
            else if (n.text?.isNotEmpty() == true) 2
            else 1
        }
    }

    private fun findSearchSuggestions(root: AccessibilityNodeInfo, query: String): List<AccessibilityNodeInfo> {
        val cleanQuery = query.lowercase().replace("'", "").trim()
        val results = mutableListOf<AccessibilityNodeInfo>()
        val matches = NodeHierarchyScanner.findNodesByText(root, cleanQuery, exactMatch = false)
        for (node in matches) {
            val cls = node.className?.toString() ?: ""
            if (!node.isEditable && !cls.contains("EditText", ignoreCase = true)) {
                results.add(node)
            }
        }
        return results
    }

    private fun submitSearch(root: AccessibilityNodeInfo) {
        val editables = findAllEditableNodes(root)
        for (node in editables) {
            try {
                node.performAction(AccessibilityNodeInfo.ACTION_NEXT_AT_MOVEMENT_GRANULARITY)
            } catch (_: Exception) {}
        }
    }

    // ================== STEP 3: SELECT RESTAURANT ==================

    private fun executeSelectRestaurant(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target missing.")
        val swiggyRoot = resolveRoot(root) ?: return fail(step, screen, "Swiggy not loaded.")

        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }
        val isMenuPage = allTexts.any {
            it.contains("recommended") || it.contains("bestseller") ||
                    it.contains("menu") || it.contains("search in menu") ||
                    it.contains("veg only") || it.contains("non-veg")
        }
        if (isMenuPage) {
            return ok(step, screen, "Selected restaurant '$target' (menu loaded)")
        }

        val restTabs = NodeHierarchyScanner.findNodesByText(swiggyRoot, "restaurants", exactMatch = true)
        for (tab in restTabs) {
            if (tab.isClickable) {
                tab.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }
        }

        val matchingNodes = findAllMatchingNodes(swiggyRoot, target)

        if (matchingNodes.size > 1) {
            Log.i(TAG, "Found ${matchingNodes.size} restaurants matching '$target'")
            val options = matchingNodes.mapIndexed { index, node ->
                val name = node.text?.toString() ?: target
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

        val targetNode = matchingNodes.firstOrNull() ?: findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            GestureDispatcher.clickNode(clickable, service)
            Log.i(TAG, "Clicked restaurant node for '$target'")
            return ok(step, screen, "Selected restaurant '$target'")
        }

        GestureDispatcher.swipeVertical(service, 500f, 1200f, 600f, 300L)
        return fail(step, screen, "Looking for '$target' restaurant...")
    }

    private fun extractAddressForNode(node: AccessibilityNodeInfo): String {
        try {
            val parent = node.parent ?: return ""
            for (i in 0 until parent.childCount) {
                val sibling = parent.getChild(i) ?: continue
                if (sibling == node) continue
                val sibText = sibling.text?.toString() ?: ""
                val sibId = sibling.viewIdResourceName?.lowercase() ?: ""
                if (sibId.contains("area") || sibId.contains("address") || sibId.contains("subtitle") || sibId.contains("location")) {
                    return sibText
                }
                if (sibText.contains(",") || sibText.contains("nagar", ignoreCase = true) || sibText.contains("road", ignoreCase = true)) {
                    return sibText
                }
            }
        } catch (e: Exception) {
            Log.d(TAG, "Error extracting address: ${e.message}")
        }
        return ""
    }

    // ================== STEP 4: SEARCH MENU ITEM ==================

    private fun executeSearchMenuItem(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val itemName = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = resolveRoot(root) ?: return fail(step, screen, "Swiggy not loaded.")

        if (isTargetVisibleOnScreen(swiggyRoot, itemName)) {
            return ok(step, screen, "Found '$itemName' on menu")
        }

        val inMenuSearch = NodeHierarchyScanner.findNodesByText(swiggyRoot, "search in menu", exactMatch = false) +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/search_in_menu")
        if (inMenuSearch.isNotEmpty()) {
            val bar = inMenuSearch.first()
            val clickable = findClickableAncestor(bar) ?: bar
            GestureDispatcher.clickNode(clickable, service)
            val editables = findAllEditableNodes(swiggyRoot)
            if (editables.isNotEmpty()) {
                GestureDispatcher.setText(service, editables.first(), itemName)
                submitSearch(swiggyRoot)
            }
        }

        return ok(step, screen, "Ready to select item '$itemName'")
    }

    // ================== STEP 5: SELECT ITEM ==================

    private fun executeSelectItem(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Item name missing.")
        val swiggyRoot = resolveRoot(root) ?: return fail(step, screen, "Swiggy not loaded.")

        val targetNode = findBestMatchingNode(swiggyRoot, target)
        if (targetNode != null) {
            val clickable = findClickableAncestor(targetNode) ?: targetNode
            GestureDispatcher.clickNode(clickable, service)
            return ok(step, screen, "Selected item '$target'")
        }

        return ok(step, screen, "Item '$target' ready for adding")
    }

    // ================== STEP 6: ADD TO CART ==================

    private fun executeAddToCart(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val target = step.target_value ?: "Item"
        val swiggyRoot = resolveRoot(root) ?: return fail(step, screen, "Swiggy not loaded.")
        val dm = service.resources.displayMetrics

        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(swiggyRoot).map { it.lowercase() }
        if (allTexts.any { it.contains("view cart") || it.contains("item added") || it.contains("checkout") }) {
            return ok(step, screen, "Item added! View Cart bar is visible.")
        }

        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item to cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "apply", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "next", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
            return ok(step, screen, "Confirmed item on customization sheet.")
        }

        val addButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add", exactMatch = true) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "+ add", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "+", exactMatch = true) +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/add_button") +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/btn_add") +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/quantity_add")

        if (addButtons.isNotEmpty()) {
            val btn = addButtons.firstOrNull { it.isClickable } ?: addButtons.first()
            val clickable = findClickableAncestor(btn) ?: btn
            GestureDispatcher.clickNode(clickable, service)
            Log.i(TAG, "Clicked ADD button for '$target'")

            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
            return ok(step, screen, "Tapped ADD for '$target'")
        }

        val dishNode = findBestMatchingNode(swiggyRoot, target)
        if (dishNode != null) {
            val clickable = findClickableAncestor(dishNode) ?: dishNode
            GestureDispatcher.clickNode(clickable, service)
            return ok(step, screen, "Clicked dish card '$target'")
        }

        GestureDispatcher.swipeVertical(service, 500f, 1200f, 600f, 300L)
        return fail(step, screen, "Looking for '$target' to add to cart...")
    }

    // ================== STEP 7: VIEW CART ==================

    private fun executeViewCart(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val swiggyRoot = resolveRoot(root) ?: return fail(step, screen, "Swiggy not loaded.")
        val dm = service.resources.displayMetrics

        val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false)
        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
            GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.94f, 80L)
        }

        val cartButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "view cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "checkout", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "review order", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(swiggyRoot, "item added", exactMatch = false) +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/view_cart_button") +
                NodeHierarchyScanner.findNodesByResourceId(swiggyRoot, "in.swiggy.android:id/floating_cart_layout")

        if (cartButtons.isNotEmpty()) {
            val btn = cartButtons.firstOrNull { it.isClickable } ?: cartButtons.first()
            val clickable = findClickableAncestor(btn) ?: btn
            GestureDispatcher.clickNode(clickable, service)
        }

        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels / 2f, dm.heightPixels * 0.93f, 80L)
        GestureDispatcher.clickAtCoordinates(service, dm.widthPixels * 0.85f, dm.heightPixels * 0.93f, 80L)

        return ok(step, screen, "Navigated to Cart / Checkout")
    }

    // ================== CUSTOMIZATION ==================

    private fun executeApplyCustomization(step: OrderStepDto, screen: ScreenType, root: AccessibilityNodeInfo?): StepExecutionResultDto {
        val swiggyRoot = resolveRoot(root)
        if (swiggyRoot != null) {
            val confirmButtons = NodeHierarchyScanner.findNodesByText(swiggyRoot, "add item", exactMatch = false) +
                    NodeHierarchyScanner.findNodesByText(swiggyRoot, "continue", exactMatch = false) +
                    NodeHierarchyScanner.findNodesByText(swiggyRoot, "done", exactMatch = false)

            if (confirmButtons.isNotEmpty()) {
                val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
                GestureDispatcher.clickNode(btn, service)
            }
        }

        return ok(step, screen, "Processed customizations")
    }

    // ================== CORE HELPERS ==================

    private fun isTargetVisibleOnScreen(root: AccessibilityNodeInfo, query: String): Boolean {
        val cleanQuery = query.lowercase().replace("'", "").replace("\u2019", "").trim()
        val allTexts = NodeHierarchyScanner.extractAllVisibleTexts(root).map { it.lowercase() }
        for (text in allTexts) {
            if (text.contains(cleanQuery) || cleanQuery.contains(text)) return true
        }
        val words = cleanQuery.split(" ").filter { it.length >= 4 }
        for (word in words) {
            for (text in allTexts) {
                if (text.contains(word)) return true
            }
        }
        return false
    }

    private fun findBestMatchingNode(root: AccessibilityNodeInfo, target: String): AccessibilityNodeInfo? {
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()
        var matches = NodeHierarchyScanner.findNodesByText(root, target, exactMatch = false)
        if (matches.isEmpty()) matches = NodeHierarchyScanner.findNodesByText(root, cleanTarget, exactMatch = false)
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

    private fun findAllMatchingNodes(root: AccessibilityNodeInfo, target: String): List<AccessibilityNodeInfo> {
        val cleanTarget = target.lowercase().replace("'", "").replace("\u2019", "").trim()
        var matches = NodeHierarchyScanner.findNodesByText(root, target, exactMatch = false)
        if (matches.isEmpty()) matches = NodeHierarchyScanner.findNodesByText(root, cleanTarget, exactMatch = false)

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

    private fun findAllEditableNodes(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val rootPkg = root.packageName?.toString() ?: ""
        if (rootPkg.contains("foodordering")) return emptyList() // Never touch Quasis own UI

        val results = mutableListOf<AccessibilityNodeInfo>()
        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val cls = node.className?.toString() ?: ""
            val id = node.viewIdResourceName?.lowercase() ?: ""
            if (id.contains("etserverurl") || id.contains("etorderprompt")) return

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
        Log.w(TAG, "STEP FAILED [${step.step_type}] screen=$screen msg=$msg")
        val dump = dumpHierarchyForDebugging(step)
        val fullMsg = if (dump.isNotBlank()) "$msg\n$dump" else msg
        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = false,
            observed_screen = screen.name,
            message = fullMsg
        )
    }

    /**
     * Dumps a compact summary of what's actually on screen whenever a step fails — both to
     * logcat (`adb logcat -s StepExecutor:W`) AND as a short string that gets appended to the
     * on-screen "Order Failed" message, so it's readable straight off the phone without adb.
     * Prioritizes clickable/editable nodes and anything id/text/desc-related to "search", since
     * that's almost always what a SEARCH_RESTAURANT failure needs to diagnose.
     */
    private fun dumpHierarchyForDebugging(step: OrderStepDto): String {
        try {
            val root = service.getAppRoot(SWIGGY_PKG) ?: service.getActiveRoot() ?: return ""
            val allNodes = mutableListOf<AccessibilityNodeInfo>()
            fun collect(node: AccessibilityNodeInfo?) {
                if (node == null || allNodes.size > 300) return
                allNodes.add(node)
                for (i in 0 until node.childCount) collect(node.getChild(i))
            }
            collect(root)

            fun describe(n: AccessibilityNodeInfo): String {
                val id = n.viewIdResourceName?.substringAfterLast('/') ?: "-"
                val cls = n.className?.toString()?.substringAfterLast('.') ?: "-"
                val text = n.text?.toString()?.take(25)
                val desc = n.contentDescription?.toString()?.take(25)
                val flags = (if (n.isClickable) "C" else "") + (if (n.isEditable) "E" else "")
                val b = Rect()
                n.getBoundsInScreen(b)
                return "[$cls${if (flags.isNotEmpty()) "($flags)" else ""}] id=$id txt=${text ?: desc ?: "-"} y=${b.centerY()}"
            }

            // Full dump to logcat for deep debugging on a computer.
            Log.w(TAG, "---- HIERARCHY DUMP (step=${step.step_type}, pkg=${root.packageName}) ----")
            allNodes.filter {
                !it.text.isNullOrBlank() || !it.contentDescription.isNullOrBlank() || it.viewIdResourceName != null
            }.forEach { Log.w(TAG, describe(it)) }
            Log.w(TAG, "---- END HIERARCHY DUMP ----")

            // Short on-screen summary: relevant search nodes first, then top clickable elements sorted by Y
            val relevant = allNodes.filter { n ->
                val hay = listOfNotNull(n.viewIdResourceName, n.text?.toString(), n.contentDescription?.toString())
                    .joinToString(" ").lowercase()
                hay.contains("search") || n.isEditable || hay.contains("dish") || hay.contains("restaurant")
            }.distinct().take(6)

            val clickableWithText = allNodes.filter {
                it.isClickable && (!it.text.isNullOrBlank() || !it.contentDescription.isNullOrBlank() || it.viewIdResourceName != null)
            }.distinct().sortedBy { n ->
                val b = Rect()
                n.getBoundsInScreen(b)
                b.centerY()
            }.take(10)

            val lines = mutableListOf("--- On-screen (pkg=${root.packageName?.toString()?.substringAfterLast('.') ?: "?"}) ---")
            if (relevant.isNotEmpty()) {
                lines.add("Search-related:")
                relevant.forEach { lines.add("  ${describe(it)}") }
            } else {
                lines.add("Search-related: NONE FOUND")
            }
            lines.add("Clickable elements (top-down):")
            clickableWithText.forEach { lines.add("  ${describe(it)}") }

            return lines.joinToString("\n")
        } catch (e: Exception) {
            Log.d(TAG, "Hierarchy dump failed: ${e.message}")
            return ""
        }
    }
}
