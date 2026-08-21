package com.quasis.foodordering.adapters

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.GestureDispatcher
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.models.ScreenType
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Coroutine-based asynchronous node interactions and screen transition helpers for Swiggy.
 */
object SwiggyNodeActions {

    private const val TAG = "SwiggyNodeActions"

    /**
     * Polls the active window hierarchy until a node matching the predicate is discovered or timeout expires.
     */
    suspend fun waitForNode(
        timeoutMs: Long = 10000L,
        pollIntervalMs: Long = 400L,
        rootSupplier: () -> AccessibilityNodeInfo?,
        predicate: (AccessibilityNodeInfo) -> Boolean
    ): AccessibilityNodeInfo? = withTimeoutOrNull(timeoutMs) {
        val startTime = System.currentTimeMillis()
        while (System.currentTimeMillis() - startTime < timeoutMs) {
            val root = rootSupplier()
            if (root != null) {
                val matched = findNodeMatching(root, predicate)
                if (matched != null) return@withTimeoutOrNull matched
            }
            delay(pollIntervalMs)
        }
        null
    }

    /**
     * Polls the active window hierarchy until the target screen state is detected.
     */
    suspend fun waitForScreen(
        targetScreen: ScreenType,
        timeoutMs: Long = 10000L,
        pollIntervalMs: Long = 400L,
        rootSupplier: () -> AccessibilityNodeInfo?
    ): Boolean = withTimeoutOrNull(timeoutMs) {
        val startTime = System.currentTimeMillis()
        while (System.currentTimeMillis() - startTime < timeoutMs) {
            val root = rootSupplier()
            val detected = SwiggyScreenMappings.detectScreen(root)
            if (detected == targetScreen) {
                Log.d(TAG, "Successfully transitioned to expected screen: $targetScreen")
                return@withTimeoutOrNull true
            }
            delay(pollIntervalMs)
        }
        Log.w(TAG, "Timed out waiting for screen: $targetScreen")
        false
    } ?: false

    /**
     * Clicks a target node with retry mechanism.
     */
    suspend fun clickWithRetry(
        node: AccessibilityNodeInfo?,
        service: AccessibilityService?,
        maxRetries: Int = 3,
        retryDelayMs: Long = 300L
    ): Boolean {
        if (node == null) return false

        for (attempt in 1..maxRetries) {
            val clicked = GestureDispatcher.clickNode(node, service)
            if (clicked) {
                Log.d(TAG, "Clicked node successfully on attempt $attempt")
                return true
            }
            delay(retryDelayMs)
        }
        Log.w(TAG, "Failed to click node after $maxRetries attempts")
        return false
    }

    /**
     * Scrolls vertically to search for an element containing the target text.
     */
    suspend fun scrollToFindText(
        targetText: String,
        service: AccessibilityService,
        rootSupplier: () -> AccessibilityNodeInfo?,
        maxScrolls: Int = 5
    ): AccessibilityNodeInfo? {
        val displayMetrics = service.resources.displayMetrics
        val screenWidth = displayMetrics.widthPixels.toFloat()
        val screenHeight = displayMetrics.heightPixels.toFloat()

        val startX = screenWidth / 2f
        val startY = screenHeight * 0.75f
        val endY = screenHeight * 0.25f

        for (scrollCount in 0..maxScrolls) {
            val root = rootSupplier()
            val nodes = NodeHierarchyScanner.findNodesByText(root, targetText)
            if (nodes.isNotEmpty()) {
                Log.d(TAG, "Found element '$targetText' after $scrollCount scrolls")
                return nodes.first()
            }

            if (scrollCount < maxScrolls) {
                Log.d(TAG, "Scrolling to find '$targetText' (attempt ${scrollCount + 1}/$maxScrolls)")
                GestureDispatcher.swipeVertical(service, startX, startY, endY, durationMs = 350L)
                delay(600L)
            }
        }

        Log.w(TAG, "Could not find element '$targetText' after $maxScrolls scrolls")
        return null
    }

    private fun findNodeMatching(
        node: AccessibilityNodeInfo?,
        predicate: (AccessibilityNodeInfo) -> Boolean
    ): AccessibilityNodeInfo? {
        if (node == null) return null
        if (predicate(node)) return node

        for (i in 0 until node.childCount) {
            val childMatch = findNodeMatching(node.getChild(i), predicate)
            if (childMatch != null) return childMatch
        }
        return null
    }
}
