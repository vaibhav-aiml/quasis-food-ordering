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
 * State machine managing asynchronous end-to-end plan execution with sequential step tracking.
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

        Log.i(TAG, "Starting pipeline execution for plan: ${plan.plan_id} with ${plan.steps.size} steps")

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
                Log.w(TAG, "Pipeline halted due to error.")
                return
            }

            Log.i(TAG, "--> Pipeline Step ${step.step_id}: ${step.step_type} (${step.target_value})")

            // Update state before running step
            val stateBefore = currentState?.copy(current_step_id = step.step_id) ?: return
            currentState = stateBefore
            notifyStateChange(stateBefore)

            // Step: STOP_FOR_PAYMENT
            if (step.step_type == StepType.STOP_FOR_PAYMENT) {
                val paymentResult = StepExecutionResultDto(
                    step_id = step.step_id,
                    step_type = step.step_type,
                    success = true,
                    message = "Items added to cart! Reached payment boundary. Handing over to user."
                )
                val finalState = stateBefore.copy(
                    status = ExecutionStatusDto.READY_FOR_PAYMENT,
                    completed_steps = stateBefore.completed_steps + paymentResult,
                    ready_for_payment = true
                )
                currentState = finalState
                notifyStateChange(finalState)
                Log.i(TAG, "Order pipeline successfully completed at cart milestone.")
                return
            }

            // Step: LAUNCH_APP
            if (step.step_type == StepType.LAUNCH_APP) {
                val launchResult = executor.execute(step, service.getActiveRoot())
                if (!launchResult.success && step.is_critical) {
                    abortCurrentExecution("Failed to open app: ${launchResult.message}")
                    return
                }
                val updatedState = currentState?.copy(
                    completed_steps = (currentState?.completed_steps ?: emptyList()) + launchResult
                ) ?: return
                currentState = updatedState
                notifyStateChange(updatedState)

                // Wait 3.5s for Swiggy home screen to fully render
                delay(3500)
                continue
            }

            // Reset executor state for this step
            executor.resetSearchState()

            // For UI steps (SEARCH, SELECT, ADD_TO_CART, VIEW_CART): Retry loop with polling
            val isSearchStep = step.step_type == StepType.SEARCH_RESTAURANT || step.step_type == StepType.SEARCH_MENU_ITEM
            // Give search steps more time (20s) since we need to wait for keyboard
            val timeoutMs = if (isSearchStep) 20000L else (step.timeout_seconds.coerceIn(8, 25)) * 1000L
            val startTime = System.currentTimeMillis()
            var stepSuccess = false
            var lastResult: StepExecutionResultDto? = null

            // Trigger search view once at step start if step is a search action
            if (isSearchStep) {
                executor.prepareSearchScreen()
                // Wait 3 seconds for the search screen to fully render and keyboard to appear
                delay(3000)
            }

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

                    // Adaptive delay based on step transition
                    when (step.step_type) {
                        StepType.SEARCH_RESTAURANT, StepType.SEARCH_MENU_ITEM -> delay(2500)
                        StepType.SELECT_RESTAURANT -> delay(2500)
                        StepType.ADD_TO_CART -> delay(1800)
                        StepType.VIEW_CART, StepType.PROCEED_TO_CHECKOUT -> delay(2000)
                        else -> delay(1200)
                    }
                    break
                }

                // Poll every 1s (give keyboard time to appear between retries)
                delay(1000)
            }

            if (!stepSuccess) {
                if (step.is_critical) {
                    abortCurrentExecution("Failed at step ${step.step_id} (${step.step_type}): ${lastResult?.message ?: "Timed out"}")
                    return
                } else {
                    val skippedResult = lastResult ?: StepExecutionResultDto(
                        step_id = step.step_id,
                        step_type = step.step_type,
                        success = false,
                        message = "Optional step passed."
                    )
                    val updatedState = currentState?.copy(
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + skippedResult
                    ) ?: return
                    currentState = updatedState
                    notifyStateChange(updatedState)
                }
            }
        }

        // All steps completed safely
        val finalState = currentState?.copy(
            status = ExecutionStatusDto.READY_FOR_PAYMENT,
            ready_for_payment = true
        )
        if (finalState != null) {
            currentState = finalState
            notifyStateChange(finalState)
        }
    }

    fun onAccessibilityEventReceived(event: AccessibilityEvent, rootNode: AccessibilityNodeInfo?) {
        // Accessibility event receiver
    }

    fun abortCurrentExecution(reason: String) {
        Log.w(TAG, "Aborting pipeline: $reason")
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
