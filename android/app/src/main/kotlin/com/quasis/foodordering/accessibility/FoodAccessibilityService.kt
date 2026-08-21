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

    /**
     * Get root node, preferring the active window.
     */
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

    /**
     * Explicitly find a specific app's window root by package name.
     * This is critical when our app fires an intent but the target app's
     * window might not be the "active" one yet.
     */
    fun getAppRoot(packageName: String): AccessibilityNodeInfo? {
        try {
            val allWindows = windows ?: emptyList()
            for (window in allWindows) {
                val root = window.root ?: continue
                val pkg = root.packageName?.toString() ?: continue
                if (pkg == packageName) {
                    Log.d(TAG, "Found window for $packageName (type=${window.type})")
                    return root
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error querying windows for $packageName", e)
        }

        // Fallback to active root and check package
        val activeRoot = getActiveRoot()
        if (activeRoot?.packageName?.toString() == packageName) {
            return activeRoot
        }

        Log.w(TAG, "Could not find window for $packageName. Active pkg=${activeRoot?.packageName}")
        return activeRoot
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
