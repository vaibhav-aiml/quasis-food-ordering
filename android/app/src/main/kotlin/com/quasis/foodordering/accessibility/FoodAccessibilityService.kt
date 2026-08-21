package com.quasis.foodordering.accessibility

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
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
        // Forward event / screen state update to orchestrator if an automation plan is active
        val rootNode = rootInActiveWindow
        OrderOrchestrator.onAccessibilityEventReceived(event, rootNode)
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
