package com.quasis.foodordering.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
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

    @Volatile
    private var lastEventRoot: AccessibilityNodeInfo? = null

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this

        try {
            val info = serviceInfo ?: AccessibilityServiceInfo()
            info.eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            info.flags = AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
            info.notificationTimeout = 50
            info.packageNames = null // Monitor all packages for smooth transitions
            serviceInfo = info
        } catch (e: Exception) {
            Log.w(TAG, "Error setting programmatic serviceInfo", e)
        }

        Log.i(TAG, "Quasis Food AccessibilityService connected and configured successfully.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        try {
            event.source?.let { lastEventRoot = it }
        } catch (_: Exception) {}
        val rootNode = getActiveRoot()
        OrderOrchestrator.onAccessibilityEventReceived(event, rootNode)
    }

    /**
     * Get root node, preferring the active window.
     */
    fun getActiveRoot(): AccessibilityNodeInfo? {
        val root = rootInActiveWindow
        if (root != null) return root

        try {
            val allWindows = windows ?: emptyList()
            for (w in allWindows) {
                if (w.isFocused || w.type == AccessibilityWindowInfo.TYPE_APPLICATION) {
                    val r = w.root
                    if (r != null) return r
                }
            }
            if (allWindows.isNotEmpty()) {
                val firstRoot = allWindows.first().root
                if (firstRoot != null) return firstRoot
            }
        } catch (e: Exception) {
            // ignore
        }

        return lastEventRoot
    }

    /**
     * Find root node for a specific package, strictly matching the focused or active window
     * on the real device screen.
     */
    fun getAppRoot(packageName: String): AccessibilityNodeInfo? {
        // 1. Check true active window on screen
        val active = rootInActiveWindow
        val activePkg = active?.packageName?.toString() ?: ""
        if (activePkg == packageName || activePkg.contains("swiggy", ignoreCase = true)) {
            if (active != null && active.childCount > 0) return active
        }

        // 2. Check focused or active application window from window manager
        try {
            val allWindows = windows ?: emptyList()
            for (window in allWindows) {
                if (window.isFocused || window.isActive || window.type == AccessibilityWindowInfo.TYPE_APPLICATION) {
                    val root = window.root ?: continue
                    val pkg = root.packageName?.toString() ?: continue
                    if (pkg == packageName || pkg.contains("swiggy", ignoreCase = true)) {
                        if (root.childCount > 0) return root
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error querying windows for $packageName", e)
        }

        // 3. Check most recent accessibility event root
        val last = lastEventRoot
        val lastPkg = last?.packageName?.toString() ?: ""
        if (lastPkg == packageName || lastPkg.contains("swiggy", ignoreCase = true)) {
            if (last != null && last.childCount > 0) return last
        }

        return null
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
