package com.quasis.foodordering.models

import kotlinx.serialization.Serializable

@Serializable
enum class StepType {
    LAUNCH_APP,
    SEARCH_RESTAURANT,
    SELECT_RESTAURANT,
    SEARCH_MENU_ITEM,
    SELECT_ITEM,
    APPLY_CUSTOMIZATION,
    ADD_TO_CART,
    VIEW_CART,
    PROCEED_TO_CHECKOUT,
    STOP_FOR_PAYMENT
}
