package com.quasis.foodordering

import com.quasis.foodordering.adapters.FoodAdapterRegistry
import com.quasis.foodordering.adapters.SwiggyAdapter
import com.quasis.foodordering.engine.ExecutionSafetyGuard
import com.quasis.foodordering.models.ScreenType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SwiggyAdapterTest {

    @Test
    fun testSwiggyAdapterMetadata() {
        val adapter = SwiggyAdapter()
        assertEquals("swiggy", adapter.appId)
        assertEquals("Swiggy", adapter.appName)
        assertEquals("in.swiggy.android", adapter.packageName)
    }

    @Test
    fun testRegistryLookup() {
        val swiggyLower = FoodAdapterRegistry.getAdapter("swiggy")
        val swiggyUpper = FoodAdapterRegistry.getAdapter("Swiggy")
        assertNotNull(swiggyLower)
        assertNotNull(swiggyUpper)
        assertEquals(swiggyLower?.appId, swiggyUpper?.appId)
    }

    @Test
    fun testPaymentSafetyRuleEnforced() {
        // Verify payment halt condition is detected for checkout screen
        assertTrue(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.CHECKOUT_PAYMENT))
        assertFalse(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.HOME))
        assertFalse(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.SEARCH))
        assertFalse(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.RESTAURANT_MENU))
    }
}
