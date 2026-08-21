package com.quasis.foodordering

import com.quasis.foodordering.adapters.FoodAdapterRegistry
import com.quasis.foodordering.adapters.SwiggyAdapter
import com.quasis.foodordering.adapters.SwiggyScreenMappings
import com.quasis.foodordering.models.ScreenType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SwiggyScreenMappingsTest {

    @Test
    fun testSwiggyPackageNameAndRegistry() {
        assertEquals("in.swiggy.android", SwiggyScreenMappings.PACKAGE_NAME)

        val adapter = FoodAdapterRegistry.getAdapter("swiggy")
        assertNotNull("Expected Swiggy adapter to be registered", adapter)
        assertEquals("swiggy", adapter?.appId)
        assertEquals("in.swiggy.android", adapter?.packageName)
    }

    @Test
    fun testResourceIdsAreDefined() {
        assertTrue(SwiggyScreenMappings.ResourceIds.SEARCH_EDIT_TEXT.contains("in.swiggy.android"))
        assertTrue(SwiggyScreenMappings.ResourceIds.RESTAURANT_NAME.contains("in.swiggy.android"))
        assertTrue(SwiggyScreenMappings.ResourceIds.MENU_ITEM_NAME.contains("in.swiggy.android"))
        assertTrue(SwiggyScreenMappings.ResourceIds.ADD_BUTTON.contains("in.swiggy.android"))
        assertTrue(SwiggyScreenMappings.ResourceIds.VIEW_CART_BUTTON.contains("in.swiggy.android"))
        assertTrue(SwiggyScreenMappings.ResourceIds.CHECKOUT_BUTTON.contains("in.swiggy.android"))
    }

    @Test
    fun testNullRootReturnsUnknownScreen() {
        val screen = SwiggyScreenMappings.detectScreen(null)
        assertEquals(ScreenType.UNKNOWN, screen)
    }
}
