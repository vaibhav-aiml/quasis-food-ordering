package com.quasis.foodordering.models

import kotlinx.serialization.Serializable

@Serializable
data class FoodItemDto(
    val name: String,
    val quantity: Int = 1,
    val portion_or_size: String? = null,
    val customizations: List<String> = emptyList(),
    val preferred_restaurant: String? = null
)

@Serializable
data class OrderPlanDto(
    val plan_id: String,
    val target_app: String = "swiggy",
    val restaurant_name: String? = null,
    val items: List<FoodItemDto> = emptyList(),
    val steps: List<OrderStepDto> = emptyList(),
    val stop_before_payment: Boolean = true
)
