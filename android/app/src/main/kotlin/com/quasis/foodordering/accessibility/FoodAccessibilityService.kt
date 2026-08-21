package com.quasis.foodordering.accessibility

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo
import com.quasis.foodordering.engine.OrderOrchestrator

/**
 * Android AccessibilityService that powers the Quasis Food Ordering Assistant.
 */
class FoodAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "FoodAccessibilitySvc"

        @Volatile
        var instance: FoodAccessibilityService? = null
            private set

        fun isRunning(): Boolean = instance != null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Quasis Food AccessibilityService connected successfully.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val rootNode = getActiveRoot()
        OrderOrchestrator.onAccessibilityEventReceived(event, rootNode)
    }

    fun getActiveRoot(): AccessibilityNodeInfo? {
        val root = rootInActiveWindow
        if (root != null) return root

        return try {
            windows?.firstOrNull { it.isFocused || it.type == AccessibilityWindowInfo.TYPE_APPLICATION }?.root
                ?: windows?.firstOrNull()?.root
        } catch (e: Exception) {
            null
        }
    }

    override fun onInterrupt() {
        Log.w(TAG, "AccessibilityService interrupted.")
        OrderOrchestrator.abortCurrentExecution("AccessibilityService was interrupted by system.")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "AccessibilityService destroyed.")
    }
}
