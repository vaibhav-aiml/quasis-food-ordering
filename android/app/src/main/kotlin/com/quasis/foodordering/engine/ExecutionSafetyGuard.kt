package com.quasis.foodordering.engine

import com.quasis.foodordering.models.OrderStepDto
import com.quasis.foodordering.models.ScreenType
import com.quasis.foodordering.models.StepType

/**
 * Hard Safety Boundary that guarantees automation stops BEFORE any payment confirmation.
 *
 * CRITICAL SAFETY RULES:
 * 1. Never automatically click "Pay", "Place Order", "Pay Now", "Proceed to Pay".
 * 2. If the current screen is detected as CHECKOUT_PAYMENT, halt execution immediately.
 * 3. Step STOP_FOR_PAYMENT forces status to READY_FOR_PAYMENT and terminates automation.
 */
object ExecutionSafetyGuard {

    private val DANGEROUS_PAYMENT_TEXTS = listOf(
        "pay now",
        "proceed to pay",
        "make payment",
        "place order",
        "confirm payment",
        "pay using",
        "complete order",
        "pay ₹",
        "pay rs"
    )

    /**
     * Checks whether an intended UI interaction targets a dangerous payment confirmation action.
     */
    fun isDangerousPaymentInteraction(targetText: String?): Boolean {
        if (targetText.isNullOrBlank()) return false
        val clean = targetText.trim().lowercase()
        return DANGEROUS_PAYMENT_TEXTS.any { clean.contains(it) }
    }

    /**
     * Checks if an OrderStepDto is an explicit STOP_FOR_PAYMENT step.
     */
    fun isStopForPaymentStep(step: OrderStepDto): Boolean {
        return step.step_type == StepType.STOP_FOR_PAYMENT ||
                step.target_value?.lowercase()?.contains("payment") == true
    }

    /**
     * Checks if the detected screen requires automation to halt immediately.
     */
    fun isPaymentScreenHaltRequired(screenType: ScreenType): Boolean {
        return screenType == ScreenType.CHECKOUT_PAYMENT
    }

    /**
     * Evaluates whether a proposed step is safe to execute.
     * Returns null if safe, or a safety violation message if dangerous.
     */
    fun validateStepSafety(step: OrderStepDto, currentScreen: ScreenType): String? {
        if (isStopForPaymentStep(step)) {
            return "SAFETY_HALT: Reached final STOP_FOR_PAYMENT milestone. Handing over to user."
        }

        if (isPaymentScreenHaltRequired(currentScreen)) {
            return "SAFETY_HALT: Payment screen detected. Automation stopped for user verification."
        }

        if (isDangerousPaymentInteraction(step.target_value)) {
            return "SAFETY_VIOLATION: Attempted action '${step.target_value}' is a forbidden payment interaction."
        }

        return null
    }
}
