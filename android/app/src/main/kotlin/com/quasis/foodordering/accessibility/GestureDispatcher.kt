package com.quasis.foodordering.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Dispatches clicks, gestures, swipes, and text injection to Android UI components.
 */
object GestureDispatcher {

    /**
     * Clicks an AccessibilityNodeInfo. Tries native ACTION_CLICK, falls back to dispatchGesture.
     */
    fun clickNode(
        node: AccessibilityNodeInfo?,
        service: AccessibilityService? = null
    ): Boolean {
        if (node == null) return false

        val clickableTarget = NodeHierarchyScanner.findClickableTarget(node)
        if (clickableTarget != null && clickableTarget.isClickable) {
            val clicked = clickableTarget.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            if (clicked) return true
        }

        // Fallback to gesture coordinates if service is available
        if (service != null) {
            val bounds = Rect()
            node.getBoundsInScreen(bounds)
            if (!bounds.isEmpty) {
                val x = bounds.centerX().toFloat()
                val y = bounds.centerY().toFloat()
                return clickAtCoordinates(service, x, y)
            }
        }

        return false
    }

    /**
     * Sets text into an editable AccessibilityNodeInfo.
     */
    fun setText(node: AccessibilityNodeInfo?, text: String): Boolean {
        if (node == null) return false
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    /**
     * Performs a tap at specific screen coordinates using AccessibilityService.dispatchGesture.
     */
    fun clickAtCoordinates(
        service: AccessibilityService,
        x: Float,
        y: Float,
        durationMs: Long = 50L
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
