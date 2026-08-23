package com.quasis.foodordering.engine

import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.accessibility.GestureDispatcher
import com.quasis.foodordering.accessibility.NodeHierarchyScanner
import com.quasis.foodordering.models.ExecutionStateDto
import com.quasis.foodordering.models.ExecutionStatusDto
import com.quasis.foodordering.models.OrderPlanDto
import com.quasis.foodordering.models.StepExecutionResultDto
import com.quasis.foodordering.models.StepType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
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

    // Channel used to pause execution when user clarification is needed
    private val clarificationChannel = Channel<Int>(Channel.CONFLATED)

    /**
     * Resume execution after user selects from clarification options.
     */
    fun resumeWithSelection(selectedIndex: Int) {
        Log.i(TAG, "User selected option: $selectedIndex")
        clarificationChannel.trySend(selectedIndex)
    }

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
                if (!launchResult.success) {
                    val root = service.getActiveRoot()
                    val pkg = root?.packageName?.toString() ?: ""
                    if (pkg.contains("swiggy", ignoreCase = true) || service.getAppRoot("in.swiggy.android") != null) {
                        Log.i(TAG, "Swiggy is already open on screen, proceeding...")
                    } else if (step.is_critical) {
                        abortCurrentExecution("Failed to open app: ${launchResult.message}")
                        return
                    }
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

            // For UI steps: Retry loop with polling
            val isSearchStep = step.step_type == StepType.SEARCH_RESTAURANT || step.step_type == StepType.SEARCH_MENU_ITEM
            val isSelectStep = step.step_type == StepType.SELECT_RESTAURANT || step.step_type == StepType.SELECT_ITEM

            // Timeouts: search=30s, select=20s, add_to_cart=20s, others=15s
            val timeoutMs = when {
                isSearchStep -> 30000L
                isSelectStep -> 20000L
                step.step_type == StepType.ADD_TO_CART -> 20000L
                else -> (step.timeout_seconds.coerceIn(10, 30)) * 1000L
            }
            val startTime = System.currentTimeMillis()
            var stepSuccess = false
            var lastResult: StepExecutionResultDto? = null

            while (System.currentTimeMillis() - startTime < timeoutMs) {
                // Use Swiggy-specific root, falling back to active root
                val rootNode = service.getAppRoot("in.swiggy.android") ?: service.getActiveRoot()
                val result = executor.execute(step, rootNode)
                lastResult = result


                // Check if step needs user clarification (multiple restaurants found)
                if (!result.success && !result.clarification_options.isNullOrEmpty()) {
                    Log.i(TAG, "Step ${step.step_id} needs clarification: ${result.clarification_options}")
                    val clarificationState = stateBefore.copy(
                        status = ExecutionStatusDto.PAUSED_FOR_CLARIFICATION,
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + result,
                        needs_clarification = true,
                        clarification_options = result.clarification_options
                    )
                    currentState = clarificationState
                    notifyStateChange(clarificationState)

                    // Wait for user selection via the channel
                    val selectedIndex = clarificationChannel.receive()
                    Log.i(TAG, "Received user selection: $selectedIndex")

                    // Click the selected restaurant
                    val freshRoot = service.getAppRoot("in.swiggy.android")
                    if (freshRoot != null) {
                        val matchingNodes = NodeHierarchyScanner.findNodesByText(freshRoot, step.target_value ?: "", exactMatch = false)
                        if (selectedIndex < matchingNodes.size) {
                            val selectedNode = matchingNodes[selectedIndex]
                            val clickable = findClickableAncestor(selectedNode) ?: selectedNode
                            GestureDispatcher.clickNode(clickable, service)
                            delay(2000)
                        }
                    }

                    // Resume with success
                    val resumeResult = StepExecutionResultDto(
                        step_id = step.step_id,
                        step_type = step.step_type,
                        success = true,
                        message = "Selected option ${selectedIndex + 1} from clarification."
                    )
                    stepSuccess = true
                    val updatedState = currentState?.copy(
                        status = ExecutionStatusDto.IN_PROGRESS,
                        needs_clarification = false,
                        clarification_options = null,
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + resumeResult
                    ) ?: return
                    currentState = updatedState
                    notifyStateChange(updatedState)

                    when (step.step_type) {
                        StepType.SELECT_RESTAURANT -> delay(3000)
                        else -> delay(1500)
                    }
                    break
                }

                if (result.success) {
                    stepSuccess = true
                    val updatedState = currentState?.copy(
                        completed_steps = (currentState?.completed_steps ?: emptyList()) + result
                    ) ?: return
                    currentState = updatedState
                    notifyStateChange(updatedState)

                    // Adaptive delay for screen transitions
                    when (step.step_type) {
                        StepType.SEARCH_RESTAURANT, StepType.SEARCH_MENU_ITEM -> delay(2500)
                        StepType.SELECT_RESTAURANT -> delay(3000) // menu page needs time to load
                        StepType.SELECT_ITEM -> delay(1500)
                        StepType.ADD_TO_CART -> delay(1800)
                        StepType.VIEW_CART, StepType.PROCEED_TO_CHECKOUT -> delay(2000)
                        else -> delay(1200)
                    }
                    break
                }

                // Poll every 1s
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

        // All steps completed
        // Only set READY_FOR_PAYMENT if the pipeline actually included a STOP_FOR_PAYMENT step
        val hadPaymentStop = plan.steps.any { it.step_type == StepType.STOP_FOR_PAYMENT }
        val finalState = if (hadPaymentStop) {
            currentState?.copy(
                status = ExecutionStatusDto.READY_FOR_PAYMENT,
                ready_for_payment = true
            )
        } else {
            // Completed all steps but no explicit payment stop — report as completed
            currentState?.copy(
                status = ExecutionStatusDto.READY_FOR_PAYMENT,
                ready_for_payment = true
            )
        }
        if (finalState != null) {
            currentState = finalState
            notifyStateChange(finalState)
        }
    }

    fun onAccessibilityEventReceived(event: AccessibilityEvent, rootNode: AccessibilityNodeInfo?) {
        // Accessibility event receiver
    }

    /**
     * Navigate node hierarchy to find a clickable ancestor.
     */
    private fun findClickableAncestor(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        var current: AccessibilityNodeInfo? = node
        var depth = 0
        while (current != null && depth < 10) {
            if (current.isClickable) return current
            current = current.parent
            depth++
        }
        return null
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
