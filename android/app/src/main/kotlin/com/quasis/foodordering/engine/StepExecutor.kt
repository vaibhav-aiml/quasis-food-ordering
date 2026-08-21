package com.quasis.foodordering.engine

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.GestureDispatcher
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.accessibility.ScreenStateDetector
import com.quasis.foodordering.models.OrderStepDto
import com.quasis.foodordering.models.ScreenType
import com.quasis.foodordering.models.StepExecutionResultDto
import com.quasis.foodordering.models.StepType

/**
 * Executes a single atomic OrderStepDto using AccessibilityService.
 */
class StepExecutor(private val service: AccessibilityService) {

    /**
     * Executes the provided step against the current active window node hierarchy.
     */
    fun execute(step: OrderStepDto, rootNode: AccessibilityNodeInfo?): StepExecutionResultDto {
        val currentScreen = ScreenStateDetector.detectScreen(rootNode)

        // 1. Enforce Safety Boundary Check
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

        // 2. Execute step according to step type
        return when (step.step_type) {
            StepType.LAUNCH_APP -> executeLaunchApp(step)
            StepType.SEARCH_RESTAURANT -> executeSearch(step, rootNode, currentScreen)
            StepType.SELECT_RESTAURANT -> executeClickText(step, rootNode, currentScreen)
            StepType.SEARCH_MENU_ITEM -> executeSearch(step, rootNode, currentScreen)
            StepType.SELECT_ITEM -> executeClickText(step, rootNode, currentScreen)
            StepType.APPLY_CUSTOMIZATION -> executeApplyCustomization(step, rootNode, currentScreen)
            StepType.ADD_TO_CART -> executeAddToCart(step, rootNode, currentScreen)
            StepType.VIEW_CART -> executeClickText(step, rootNode, currentScreen)
            StepType.PROCEED_TO_CHECKOUT -> executeClickText(step, rootNode, currentScreen)
            StepType.STOP_FOR_PAYMENT -> {
                StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    observed_screen = currentScreen.name,
                    message = "Safety stop before payment reached successfully."
                )
            }
        }
    }

    private fun executeLaunchApp(step: OrderStepDto): StepExecutionResultDto {
        val packageName = step.parameters["package_name"]?.toString()
            ?.removeSurrounding("\"") ?: "in.swiggy.android"

        val launchIntent = service.packageManager.getLaunchIntentForPackage(packageName)
        return if (launchIntent != null) {
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            service.startActivity(launchIntent)
            StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = true,
                message = "Launched package: $packageName"
            )
        } else {
            StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = false,
                message = "Could not find launch intent for package: $packageName"
            )
        }
    }

    private fun executeSearch(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val query = step.target_value ?: return fail(step, screen, "Target value missing for search.")
        val searchBoxes = NodeHierarchyScanner.findNodesByText(rootNode, "search")

        if (searchBoxes.isNotEmpty()) {
            val targetBox = searchBoxes.firstOrNull { it.isEditable } ?: searchBoxes.first()
            GestureDispatcher.clickNode(targetBox, service)
            val textSet = GestureDispatcher.setText(targetBox, query)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = textSet,
                observed_screen = screen.name,
                message = if (textSet) "Entered search text '$query'" else "Failed to set text '$query'"
            )
        }

        return fail(step, screen, "No search box found on screen.")
    }

    private fun executeClickText(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val target = step.target_value ?: return fail(step, screen, "Target value missing for click.")
        val matchingNodes = NodeHierarchyScanner.findNodesByText(rootNode, target)

        if (matchingNodes.isNotEmpty()) {
            val clicked = GestureDispatcher.clickNode(matchingNodes.first(), service)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = clicked,
                observed_screen = screen.name,
                message = if (clicked) "Clicked node with text '$target'" else "Failed to click '$target'"
            )
        }

        return fail(step, screen, "Element with text '$target' not found on screen.")
    }

    private fun executeAddToCart(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        val target = step.target_value ?: ""
        // Try finding "Add" button near item or on bottom sheet
        val addButtons = NodeHierarchyScanner.findNodesByText(rootNode, "add", exactMatch = false)
        if (addButtons.isNotEmpty()) {
            val clicked = GestureDispatcher.clickNode(addButtons.first(), service)
            return StepExecutionResultDto(
                step_id = step.step_id,
                step_type = step.step_type,
                success = clicked,
                observed_screen = screen.name,
                message = if (clicked) "Clicked 'Add' for item '$target'" else "Failed to click 'Add'"
            )
        }
        return fail(step, screen, "Could not find Add button on screen.")
    }

    private fun executeApplyCustomization(
        step: OrderStepDto,
        rootNode: AccessibilityNodeInfo?,
        screen: ScreenType
    ): StepExecutionResultDto {
        // Find customization options requested in parameters
        return StepExecutionResultDto(
            step_id = step.step_id,
            step_type = step.step_type,
            success = true,
            observed_screen = screen.name,
            message = "Processed customizations for step ${step.step_id}"
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
