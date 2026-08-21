package com.quasis.foodordering.engine

import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.models.ExecutionStateDto
import com.quasis.foodordering.models.ExecutionStatusDto
import com.quasis.foodordering.models.OrderPlanDto
import com.quasis.foodordering.models.StepExecutionResultDto
import com.quasis.foodordering.models.StepType

/**
 * State machine managing end-to-end plan execution with sequential step tracking.
 */
object OrderOrchestrator {

    private const val TAG = "OrderOrchestrator"

    @Volatile
    private var activePlan: OrderPlanDto? = null

    @Volatile
    private var currentState: ExecutionStateDto? = null

    var stateChangeListener: ((ExecutionStateDto) -> Unit)? = null

    /**
     * Start execution of a validated OrderPlan.
     */
    fun startExecution(plan: OrderPlanDto): ExecutionStateDto {
        activePlan = plan
        val state = ExecutionStateDto(
            plan_id = plan.plan_id,
            current_step_id = 1,
            status = ExecutionStatusDto.IN_PROGRESS,
            completed_steps = emptyList(),
            ready_for_payment = false
        )
        currentState = state
        notifyStateChange(state)

        Log.i(TAG, "Starting execution for plan: ${plan.plan_id} with ${plan.steps.size} steps")
        executeNextStep()
        return currentState ?: state
    }

    /**
     * Triggers execution of the next step in the plan.
     */
    fun executeNextStep() {
        val plan = activePlan ?: return
        val state = currentState ?: return
        val service = FoodAccessibilityService.instance

        if (service == null) {
            abortCurrentExecution("AccessibilityService is not enabled or running.")
            return
        }

        val stepIndex = state.current_step_id - 1
        if (stepIndex >= plan.steps.size) {
            // Plan completed
            val finalState = state.copy(
                status = ExecutionStatusDto.READY_FOR_PAYMENT,
                ready_for_payment = true
            )
            currentState = finalState
            notifyStateChange(finalState)
            Log.i(TAG, "All steps in plan ${plan.plan_id} completed successfully.")
            return
        }

        val currentStep = plan.steps[stepIndex]

        // Safety stop check
        if (currentStep.step_type == StepType.STOP_FOR_PAYMENT) {
            val paymentResult = StepExecutionResultDto(
                step_id = currentStep.step_id,
                step_type = currentStep.step_type,
                success = true,
                message = "Reached payment boundary. Handing over to user."
            )
            val finalState = state.copy(
                status = ExecutionStatusDto.READY_FOR_PAYMENT,
                completed_steps = state.completed_steps + paymentResult,
                ready_for_payment = true
            )
            currentState = finalState
            notifyStateChange(finalState)
            Log.i(TAG, "Safety stop reached for plan: ${plan.plan_id}")
            return
        }

        val executor = StepExecutor(service)
        val rootNode = service.rootInActiveWindow
        val result = executor.execute(currentStep, rootNode)

        if (result.success) {
            val updatedState = state.copy(
                current_step_id = state.current_step_id + 1,
                completed_steps = state.completed_steps + result
            )
            currentState = updatedState
            notifyStateChange(updatedState)
        } else if (currentStep.is_critical) {
            abortCurrentExecution("Failed at critical step ${currentStep.step_id} (${currentStep.step_type}): ${result.message}")
        } else {
            // Non-critical step failure (e.g. optional customization) -> continue
            val updatedState = state.copy(
                current_step_id = state.current_step_id + 1,
                completed_steps = state.completed_steps + result
            )
            currentState = updatedState
            notifyStateChange(updatedState)
        }
    }

    /**
     * Called whenever an AccessibilityEvent is received.
     */
    fun onAccessibilityEventReceived(event: AccessibilityEvent, rootNode: AccessibilityNodeInfo?) {
        // If an automated step is in progress, progress state machine on content changes
        if (currentState?.status == ExecutionStatusDto.IN_PROGRESS) {
            // Can trigger step progression on window state change
        }
    }

    /**
     * Abort execution immediately with error message.
     */
    fun abortCurrentExecution(reason: String) {
        Log.w(TAG, "Aborting execution: $reason")
        val state = currentState?.copy(
            status = ExecutionStatusDto.FAILED,
            error_message = reason
        ) ?: ExecutionStateDto(
            plan_id = activePlan?.plan_id ?: "unknown",
            status = ExecutionStatusDto.FAILED,
            error_message = reason
        )
        currentState = state
        notifyStateChange(state)
        activePlan = null
    }

    fun getCurrentState(): ExecutionStateDto? = currentState

    private fun notifyStateChange(state: ExecutionStateDto) {
        stateChangeListener?.invoke(state)
    }
}
