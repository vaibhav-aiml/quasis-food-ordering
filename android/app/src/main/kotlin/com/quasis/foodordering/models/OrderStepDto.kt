package com.quasis.foodordering.models

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class OrderStepDto(
    val step_id: Int,
    val step_type: StepType,
    val target_value: String? = null,
    val parameters: JsonObject = JsonObject(emptyMap()),
    val expected_screen: String,
    val timeout_seconds: Int = 15,
    val is_critical: Boolean = true
)
