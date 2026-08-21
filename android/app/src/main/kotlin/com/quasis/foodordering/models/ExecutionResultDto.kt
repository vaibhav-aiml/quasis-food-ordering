package com.quasis.foodordering.models

import kotlinx.serialization.Serializable

@Serializable
enum class ExecutionStatusDto {
    PENDING,
    IN_PROGRESS,
    PAUSED_FOR_CLARIFICATION,
    READY_FOR_PAYMENT,
    FAILED,
    CANCELLED
}

@Serializable
data class StepExecutionResultDto(
    val step_id: Int,
    val step_type: StepType,
    val success: Boolean,
    val observed_screen: String? = null,
    val message: String? = null,
    val screenshot_ref: String? = null
)

@Serializable
data class ExecutionStateDto(
    val plan_id: String,
    val current_step_id: Int = 1,
    val status: ExecutionStatusDto = ExecutionStatusDto.PENDING,
    val completed_steps: List<StepExecutionResultDto> = emptyList(),
    val ready_for_payment: Boolean = false,
    val error_message: String? = null
)
