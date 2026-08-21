package com.quasis.foodordering

import com.quasis.foodordering.engine.OrderOrchestrator
import com.quasis.foodordering.models.ExecutionStatusDto
import com.quasis.foodordering.models.FoodItemDto
import com.quasis.foodordering.models.OrderPlanDto
import com.quasis.foodordering.models.OrderStepDto
import com.quasis.foodordering.models.StepType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OrderOrchestratorTest {

    @Test
    fun testPlanStateInitialization() {
        val plan = OrderPlanDto(
            plan_id = "test_plan_1",
            target_app = "swiggy",
            restaurant_name = "Meghana Foods",
            items = listOf(FoodItemDto(name = "chicken biryani", quantity = 1)),
            steps = listOf(
                OrderStepDto(
                    step_id = 1,
                    step_type = StepType.STOP_FOR_PAYMENT,
                    target_value = "payment",
                    expected_screen = "payment_options"
                )
            ),
            stop_before_payment = true
        )

        val state = OrderOrchestrator.startExecution(plan)

        assertNotNull(state)
        assertEquals("test_plan_1", state.plan_id)
        // When the first step is STOP_FOR_PAYMENT, it transitions to READY_FOR_PAYMENT
        assertEquals(ExecutionStatusDto.READY_FOR_PAYMENT, state.status)
        assertTrue(state.ready_for_payment)
    }

    @Test
    fun testAbortExecutionSetsFailedState() {
        OrderOrchestrator.abortCurrentExecution("Device offline")
        val state = OrderOrchestrator.getCurrentState()
        assertNotNull(state)
        assertEquals(ExecutionStatusDto.FAILED, state!!.status)
        assertEquals("Device offline", state.error_message)
    }
}
