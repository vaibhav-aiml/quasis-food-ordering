package com.quasis.foodordering.engine

import android.content.Intent
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
 */
class StepExecutor(
    private val service: FoodAccessibilityService
) {
    fun execute(step: OrderStepDto, rootNode: AccessibilityNodeInfo?): StepExecutionResultDto {
        val currentScreen = ScreenStateDetector.detectScreen(rootNode)

        // 1. Safety verification: never automate payment
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

        // 2. Dispatch to specific step action
        return when (step.step_type) {
            StepType.LAUNCH_APP -> executeLaunchApp(step)
            StepType.SEARCH_RESTAURANT -> executeSearch(step, rootNode, currentScreen)
            StepType.SELECT_RESTAURANT -> executeClickRestaurantOrDish(step, rootNode, currentScreen)
            StepType.SEARCH_MENU_ITEM -> executeSearch(step, rootNode, currentScreen)
            StepType.SELECT_ITEM -> executeClickRestaurantOrDish(step, rootNode, currentScreen)
            StepType.APPLY_CUSTOMIZATION -> executeApplyCustomization(step, rootNode, currentScreen)
            StepType.ADD_TO_CART -> executeAddToCart(step, rootNode, currentScreen)
            StepType.VIEW_CART -> executeViewCart(step, rootNode, currentScreen)
            StepType.PROCEED_TO_CHECKOUT -> executeViewCart(step, rootNode, currentScreen)
            StepType.STOP_FOR_PAYMENT -> {
                StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    observed_screen = currentScreen.name,
                    message = "Safety stop before payment reached."
                )
            }
        }
    }

    /**
     * Opens the search interface once before typing.
     */
    fun prepareSearchScreen() {
        val rootNode = service.getActiveRoot()
        val editableNodes = findEditableNodes(rootNode)
        if (editableNodes.isNotEmpty()) return

        try {
            val searchIntent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse("swiggy://search")).apply {
                setPackage("in.swiggy.android")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            service.startActivity(searchIntent)
        } catch (e: Exception) {
            val displayMetrics = service.resources.displayMetrics
            val centerX = displayMetrics.widthPixels / 2f
            val searchBarY = displayMetrics.heightPixels * 0.16f
            GestureDispatcher.clickAtCoordinates(service, centerX, searchBarY)
        }
    }

    private fun executeLaunchApp(step: OrderStepDto): StepExecutionResultDto {
        val packageName = step.parameters["package_name"]?.toString()
            ?.removeSurrounding("\"") ?: "in.swiggy.android"

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

        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = false,
            message = "Could not launch $packageName"
        )
    }

    private fun executeSearch(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Search query missing.")

        // 1. Locate editable search field
        val editableNodes = findEditableNodes(rootNode)
        if (editableNodes.isNotEmpty()) {
            val targetBox = editableNodes.first()
            GestureDispatcher.clickNode(targetBox, service)
            val textSet = GestureDispatcher.setText(targetBox, query)
            if (textSet) {
                // If auto-suggestions appear, tap the first matching suggestion
                val suggestions = NodeHierarchyScanner.findNodesByText(rootNode, query, exactMatch = false)
                val suggestionNode = suggestions.firstOrNull { it != targetBox && it.isClickable }
                if (suggestionNode != null) {
                    GestureDispatcher.clickNode(suggestionNode, service)
                }
                return StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    observed_screen = screen.name,
                    message = "Searched for '$query'"
                )
            }
        }

        // 2. If not on search input yet, click search trigger
        val searchTriggers = NodeHierarchyScanner.findNodesByText(rootNode, "search", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "dishes", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "restaurants", exactMatch = false)

        if (searchTriggers.isNotEmpty()) {
            val trigger = searchTriggers.firstOrNull { it.isClickable } ?: searchTriggers.first()
            GestureDispatcher.clickNode(trigger, service)
        }

        return fail(step, screen, "Waiting for search box to enter '$query'...")
    }

    private fun executeClickRestaurantOrDish(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target value missing.")
        val cleanTarget = target.lowercase().replace("'", "").replace("’", "").trim()

        // 1. Check exact or partial text match
        var matchingNodes = NodeHierarchyScanner.findNodesByText(rootNode, target, exactMatch = false)
        if (matchingNodes.isEmpty()) {
            matchingNodes = NodeHierarchyScanner.findNodesByText(rootNode, cleanTarget, exactMatch = false)
        }

        // 2. Keyword stems (e.g. "Domino", "Pizza", "Biryani")
        if (matchingNodes.isEmpty()) {
            val words = target.split(" ").filter { it.length >= 4 }
            for (w in words) {
                val matches = NodeHierarchyScanner.findNodesByText(rootNode, w, exactMatch = false)
                if (matches.isNotEmpty()) {
                    matchingNodes = matches
                    break
                }
            }
        }

        if (matchingNodes.isNotEmpty()) {
            val nodeToClick = matchingNodes.firstOrNull { it.isClickable } ?: matchingNodes.first()
            val clicked = GestureDispatcher.clickNode(nodeToClick, service)
            if (clicked) {
                return StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    observed_screen = screen.name,
                    message = "Selected '$target'"
                )
            }
        }

        // 3. Fallback to first search result card if available
        val resultCards = NodeHierarchyScanner.findNodesByText(rootNode, "restaurants", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "dishes", exactMatch = false)
        val firstCard = resultCards.firstOrNull { it.isClickable }
        if (firstCard != null && GestureDispatcher.clickNode(firstCard, service)) {
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                observed_screen = screen.name,
                message = "Selected first result for '$target'"
            )
        }

        // Scroll down to reveal items
        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Locating '$target' on screen...")
    }

    private fun executeAddToCart(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val target = step.target_value ?: ""

        // 1. Confirm any active customization sheet / dialog
        val confirmButtons = NodeHierarchyScanner.findNodesByText(rootNode, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "repeat last", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "apply", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = clicked,
                observed_screen = screen.name,
                message = "Confirmed item on customization sheet."
            )
        }

        // 2. Look for "ADD" buttons
        val addButtons = NodeHierarchyScanner.findNodesByText(rootNode, "add", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "+", exactMatch = true)

        if (addButtons.isNotEmpty()) {
            val btn = addButtons.firstOrNull { it.isClickable } ?: addButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = clicked,
                observed_screen = screen.name,
                message = if (clicked) "Tapped 'ADD' for $target" else "Failed to tap 'ADD'"
            )
        }

        // Scroll down to locate add button
        GestureDispatcher.swipeVertical(service, 500f, 1300f, 700f, 300L)
        return fail(step, screen, "Looking for 'ADD' button on screen...")
    }

    private fun executeViewCart(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val cartButtons = NodeHierarchyScanner.findNodesByText(rootNode, "view cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "cart", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "checkout", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "review order", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "item added", exactMatch = false)

        if (cartButtons.isNotEmpty()) {
            val btn = cartButtons.firstOrNull { it.isClickable } ?: cartButtons.first()
            val clicked = GestureDispatcher.clickNode(btn, service)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = clicked,
                observed_screen = screen.name,
                message = "Navigated to Cart / Checkout"
            )
        }

        return fail(step, screen, "Looking for Cart bar...")
    }

    private fun executeApplyCustomization(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val confirmButtons = NodeHierarchyScanner.findNodesByText(rootNode, "add item", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "continue", exactMatch = false) +
                NodeHierarchyScanner.findNodesByText(rootNode, "done", exactMatch = false)

        if (confirmButtons.isNotEmpty()) {
            val btn = confirmButtons.firstOrNull { it.isClickable } ?: confirmButtons.first()
            GestureDispatcher.clickNode(btn, service)
        }

        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = true,
            observed_screen = screen.name,
            message = "Processed customizations for step ${step.step_id}"
        )
    }

    private fun findEditableNodes(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        if (root == null) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val cls = node.className?.toString() ?: ""
            if (node.isEditable || cls.contains("EditText", ignoreCase = true) || cls.contains("AutoCompleteTextView", ignoreCase = true) || cls.contains("SearchView", ignoreCase = true)) {
                results.add(node)
            }
            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
        }

        traverse(root)
        return results
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
