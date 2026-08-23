package com.quasis.foodordering.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Dispatches clicks, gestures, swipes, and text injection to Android UI components.
 */
object GestureDispatcher {

    /**
     * Clicks an AccessibilityNodeInfo using both native ACTION_CLICK and physical gesture touch event.
     */
    fun clickNode(
        node: AccessibilityNodeInfo?,
        service: AccessibilityService? = null
    ): Boolean {
        if (node == null) return false

        val bounds = Rect()
        node.getBoundsInScreen(bounds)

        // 1. Try native ACTION_CLICK
        val clickableTarget = NodeHierarchyScanner.findClickableTarget(node)
        var actionClicked = false
        if (clickableTarget != null && clickableTarget.isClickable) {
            actionClicked = clickableTarget.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        }
        if (!actionClicked && node.isClickable) {
            actionClicked = node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        }
        if (actionClicked) return true

        // 2. FALLBACK ONLY: physical touch gesture on coordinates, used only when native ACTION_CLICK failed
        if (service != null && !bounds.isEmpty && bounds.centerX() > 0 && bounds.centerY() > 0) {
            return clickAtCoordinates(service, bounds.centerX().toFloat(), bounds.centerY().toFloat(), 80L)
        }

        return actionClicked
    }

    /**
     * Sets text into an AccessibilityNodeInfo with focus and clipboard paste fallbacks.
     */
    fun setText(
        service: AccessibilityService,
        node: AccessibilityNodeInfo?,
        text: String
    ): Boolean {
        // 1. Copy to clipboard FIRST so paste works on any focusable element
        try {
            val clipboard = service.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            if (clipboard != null) {
                val clip = ClipData.newPlainText("order_search_query", text)
                clipboard.setPrimaryClip(clip)
            }
        } catch (_: Exception) {}

        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }

        // 2. Try on the target node directly
        if (node != null) {
            if (node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) return true
            node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
            if (node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) return true
            node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            if (node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) return true
            if (node.performAction(AccessibilityNodeInfo.ACTION_PASTE)) return true
        }

        // 3. Try on the currently focused input in the active window (e.g. Compose active focus)
        val activeRoot = service.rootInActiveWindow
        val focusedInput = activeRoot?.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focusedInput != null) {
            if (focusedInput.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) return true
            if (focusedInput.performAction(AccessibilityNodeInfo.ACTION_PASTE)) return true
        }

        val focusedA11y = activeRoot?.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
        if (focusedA11y != null) {
            if (focusedA11y.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) return true
            if (focusedA11y.performAction(AccessibilityNodeInfo.ACTION_PASTE)) return true
        }

        return false
    }


    /**
     * Performs a physical tap at specific screen coordinates using AccessibilityService.dispatchGesture.
     */
    fun clickAtCoordinates(
        service: AccessibilityService,
        x: Float,
        y: Float,
        durationMs: Long = 80L
    ): Boolean {
        val path = Path().apply {
            moveTo(x, y)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()
        return service.dispatchGesture(gesture, null, null)
    }

    /**
     * Performs a vertical swipe gesture (e.g. for scrolling).
     */
    fun swipeVertical(
        service: AccessibilityService,
        startX: Float,
        startY: Float,
        endY: Float,
        durationMs: Long = 300L
    ): Boolean {
        val path = Path().apply {
            moveTo(startX, startY)
            lineTo(startX, endY)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()
        return service.dispatchGesture(gesture, null, null)
    }
}
