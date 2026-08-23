package com.quasis.foodordering.accessibility

import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Utility for scanning, traversing, and extracting nodes from an AccessibilityNodeInfo hierarchy.
 */
object NodeHierarchyScanner {

    /**
     * Find nodes matching text (exact or case-insensitive substring).
     */
    fun findNodesByText(
        root: AccessibilityNodeInfo?,
        text: String,
        exactMatch: Boolean = false
    ): List<AccessibilityNodeInfo> {
        if (root == null || text.isBlank()) return emptyList()
        val results = mutableListOf<AccessibilityNodeInfo>()
        val query = text.trim().lowercase()

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return

            val nodeText = node.text?.toString()?.trim()?.lowercase()
            val contentDesc = node.contentDescription?.toString()?.trim()?.lowercase()

            val matchesText = if (exactMatch) {
                nodeText == query || contentDesc == query
            } else {
                (nodeText?.contains(query) == true) || (contentDesc?.contains(query) == true)
            }

            if (matchesText) {
                results.add(node)
            }

            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
        }

        traverse(root)
        return results
    }

    /**
     * Find nodes by View Resource ID.
     */
    fun findNodesByResourceId(
        root: AccessibilityNodeInfo?,
        resourceId: String
    ): List<AccessibilityNodeInfo> {
        if (root == null || resourceId.isBlank()) return emptyList()
        return try {
            root.findAccessibilityNodeInfosByViewId(resourceId) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    /**
     * Finds the nearest clickable element (either the node itself or one of its ancestors).
     */
    fun findClickableTarget(node: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        var current = node
        while (current != null) {
            if (current.isClickable || current.isCheckable) {
                return current
            }
            current = current.parent
        }
        return node
    }

    /**
     * Collects all non-blank visible text across the entire hierarchy.
     */
    fun extractAllVisibleTexts(root: AccessibilityNodeInfo?): List<String> {
        if (root == null) return emptyList()
        val texts = mutableListOf<String>()

        fun traverse(node: AccessibilityNodeInfo?) {
            if (node == null) return
            val text = node.text?.toString()?.trim()
            if (!text.isNullOrEmpty()) texts.add(text)

            val desc = node.contentDescription?.toString()?.trim()
            if (!desc.isNullOrEmpty() && desc != text) texts.add(desc)

            for (i in 0 until node.childCount) {
                traverse(node.getChild(i))
            }
        }

        traverse(root)
        return texts
    }


    /**
     * Extracts screen bounds for a node.
     */
    fun getNodeBounds(node: AccessibilityNodeInfo?): Rect {
        val rect = Rect()
        node?.getBoundsInScreen(rect)
        return rect
    }
}
