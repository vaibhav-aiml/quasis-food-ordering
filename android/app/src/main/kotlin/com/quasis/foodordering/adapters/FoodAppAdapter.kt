package com.quasis.foodordering.adapters

import android.content.Context
import android.content.pm.PackageManager
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.models.ScreenType

/**
 * Common abstraction for food delivery app adapters.
 */
interface FoodAppAdapter {
    val appId: String
    val appName: String
    val packageName: String

    fun isAppInstalled(context: Context): Boolean {
        return try {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    fun detectScreen(rootNode: AccessibilityNodeInfo?): ScreenType
}
