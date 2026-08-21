package com.quasis.foodordering.engine

import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.models.ExecutionStateDto
import com.quasis.foodordering.models.ExecutionStatusDto
import com.quasis.foodordering.models.OrderPlanDto
import com.quasis.foodordering.models.StepExecutionResultDto
import com.quasis.foodordering.models.StepType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * State machine managing asynchronous end-to-end plan execution with live sequential step tracking.
 */
object OrderOrchestrator {

    private const val TAG = "OrderOrchestrator"
    private val orchestratorScope = CoroutineScope(Dispatchers.Default)
    private var executionJob: Job? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    @Volatile
    private var activePlan: OrderPlanDto? = null

    @Volatile
    private var currentState: ExecutionStateDto? = null

    var stateChangeListener: ((ExecutionStateDto) -> Unit)? = null

    /**
     * Start execution of a validated OrderPlan asynchronously.
     */
    fun startExecution(plan: OrderPlanDto): ExecutionStateDto {
        executionJob?.cancel()

        activePlan = plan
        val initialState = ExecutionStateDto(
            plan_id = plan.plan_id,
            current_step_id = 1,
            status = ExecutionStatusDto.IN_PROGRESS,
            completed_steps = emptyList(),
            ready_for_payment = false
        )
        currentState = initialState
        notifyStateChange(initialState)

        Log.i(TAG, "Starting asynchronous execution loop for plan: ${plan.plan_id} with ${plan.steps.size} steps")

        executionJob = orchestratorScope.launch {
            runPlanLoop(plan)
        }

        return initialState
    }

    private suspend fun runPlanLoop(plan: OrderPlanDto) {
        val service = FoodAccessibilityService.instance
        if (service == null) {
            abortCurrentExecution("AccessibilityService is not enabled or running.")
            return
        }

        val executor = StepExecutor(service)

        for (step in plan.steps) {
            if (currentState?.status == ExecutionStatusDto.FAILED) {
                Log.w(TAG, "Execution loop stopped because plan failed.")
                return
            }

            Log.i(TAG, "Executing Step ${step.step_id}: ${step.step_type} (target: '${step.target_value}')")

            // Update state to reflect current step being attempted
            val stateBefore = currentState?.copy(current_step_id = step.step_id) ?: return
            currentState = stateBefore
            notifyStateChange(stateBefore)

            // Step safety stop check
            if (step.step_type == StepType.STOP_FOR_PAYMENT) {
                val paymentResult = StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    message = "Reached checkout safely. Handing over to user for payment."
                )
                val finalState = stateBefore.copy(
                    status = ExecutionStatusDto.READY_FOR_PAYMENT,
                    completed_steps = stateBefore.completed_steps + paymentResult,
                    ready_for_payment = true
                )
                currentState = finalState
                notifyStateChange(finalState)
                Log.i(TAG, "Safety stop reached for plan: ${plan.plan_id}")
                return
            }

            // Step 1: LAUNCH_APP -> give it time to load splash & UI
            if (step.step_type == StepType.LAUNCH_APP) {
                val launchResult = executor.execute(step, service.getActiveRoot())
                if (!launchResult.success && step.is_critical) {
                    abortCurrentExecution("Failed at Step 1 (LAUNCH_APP): ${launchResult.message}")
                    return
                }
                val updatedState = currentState?.copy(
                    completed_steps = (currentState?.completed_steps ?: emptyList()) + launchResult
                ) ?: return
                currentState = updatedState
                notifyStateChange(updatedState)

                // Wait 3.0s for Swiggy to fully launch and display home screen
                delay(3000)
                continue
            }

            // For UI steps (SEARCH, SELECT, ADD_TO_CART, VIEW_CART, etc.), retry over step timeout
            val timeoutMs = (step.timeout_seconds.coerceIn(6, 20)) * 1000L
            val startTime = System.currentTimeMillis()
            var stepSuccess = false
            var lastResult: StepExecutionResultDto? = null

            while (System.currentTimeMillis() - startTime < timeoutMs) {
                val rootNode = service.getActiveRoot()
                val result = executor.execute(step, rootNode)
                lastResult = result

                if (result.success) {
                    stepSuccess = true
                    val updatedState = currentState?.copy(
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + result
                    ) ?: return
                    currentState = updatedState
                    notifyStateChange(updatedState)
                    // Short pause for screen transition / UI animation
                    delay(1500)
                    break
                }

                // Retry after brief delay
                delay(800)
            }

            if (!stepSuccess) {
                if (step.is_critical) {
                    abortCurrentExecution("Failed at step ${step.step_id} (${step.step_type}): ${lastResult?.message ?: "Timed out searching UI"}")
                    return
                } else {
                    // Non-critical step: record and proceed
                    val failedNonCritical = lastResult ?: StepExecutionResultDto(
                        step_id = step.step_id,
                        step_type = step.step_type,
                        success = false,
                        message = "Non-critical step skipped after timeout."
                    )
                    val updatedState = currentState?.copy(
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + failedNonCritical
                    ) ?: return
                    currentState = updatedState
                    notifyStateChange(updatedState)
                }
            }
        }

        // All steps executed
        val finalState = currentState?.copy(
            status = ExecutionStatusDto.READY_FOR_PAYMENT,
            ready_for_payment = true
        )
        if (finalState != null) {
            currentState = finalState
            notifyStateChange(finalState)
        }
    }

    /**
     * Called whenever an AccessibilityEvent is received.
     */
    fun onAccessibilityEventReceived(event: AccessibilityEvent, rootNode: AccessibilityNodeInfo?) {
        // Can be used for real-time reactivity
    }

    /**
     * Abort execution immediately with error message.
     */
    fun abortCurrentExecution(reason: String) {
        Log.w(TAG, "Aborting execution: $reason")
        executionJob?.cancel()
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
        mainHandler.post {
            stateChangeListener?.invoke(state)
        }
    }
}
