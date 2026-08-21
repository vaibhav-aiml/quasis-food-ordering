package com.quasis.foodordering

import com.quasis.foodordering.engine.ExecutionSafetyGuard
import com.quasis.foodordering.models.OrderStepDto
import com.quasis.foodordering.models.ScreenType
import com.quasis.foodordering.models.StepType
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SafetyGuardTest {

    @Test
    fun testDangerousPaymentInteractionsAreDetected() {
        val dangerousPhrases = listOf(
            "Pay Now",
            "PROCEED TO PAY",
            "Make Payment",
            "Place Order",
            "pay ₹350",
            "Pay Rs 500",
            "Confirm Payment"
        )
        for (phrase in dangerousPhrases) {
            assertTrue(
                "Expected '$phrase' to be flagged as dangerous",
                ExecutionSafetyGuard.isDangerousPaymentInteraction(phrase)
            )
        }
    }

    @Test
    fun testSafeInteractionsAreAllowed() {
        val safePhrases = listOf(
            "Meghana Foods",
            "Chicken Biryani",
            "Add to Cart",
            "Customise",
            "Extra Raita",
            "Search",
            "View Cart"
        )
        for (phrase in safePhrases) {
            assertFalse(
                "Expected '$phrase' to be allowed",
                ExecutionSafetyGuard.isDangerousPaymentInteraction(phrase)
            )
        }
    }

    @Test
    fun testPaymentScreenForcesImmediateHalt() {
        assertTrue(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.CHECKOUT_PAYMENT))
        assertFalse(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.RESTAURANT_MENU))
        assertFalse(ExecutionSafetyGuard.isPaymentScreenHaltRequired(ScreenType.CART))
    }

    @Test
    fun testStopForPaymentStepForcesHalt() {
        val stopStep = OrderStepDto(
            step_id = 10,
            step_type = StepType.STOP_FOR_PAYMENT,
            target_value = "payment",
            expected_screen = "payment_options"
        )
        val violation = ExecutionSafetyGuard.validateStepSafety(stopStep, ScreenType.CART)
        assertNotNull(violation)
        assertTrue(violation!!.contains("SAFETY_HALT"))
    }

    @Test
    fun testDangerousClickStepReturnsViolation() {
        val dangerousStep = OrderStepDto(
            step_id = 9,
            step_type = StepType.PROCEED_TO_CHECKOUT,
            target_value = "Pay Now",
            expected_screen = "cart"
        )
        val violation = ExecutionSafetyGuard.validateStepSafety(dangerousStep, ScreenType.CART)
        assertNotNull(violation)
        assertTrue(violation!!.contains("SAFETY_VIOLATION"))
    }

    @Test
    fun testSafeStepOnMenuScreenPasses() {
        val safeStep = OrderStepDto(
            step_id = 4,
            step_type = StepType.SELECT_ITEM,
            target_value = "Chicken Biryani",
            expected_screen = "restaurant_menu"
        )
        val violation = ExecutionSafetyGuard.validateStepSafety(safeStep, ScreenType.RESTAURANT_MENU)
        assertNull(violation)
    }
}
