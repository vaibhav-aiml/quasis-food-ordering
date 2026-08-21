package com.quasis.foodordering.models

import kotlinx.serialization.Serializable

@Serializable
enum class ScreenType {
    UNKNOWN,
    HOME,
    SEARCH,
    SEARCH_RESULTS,
    RESTAURANT_MENU,
    CUSTOMIZATION_SHEET,
    CART,
    CHECKOUT_PAYMENT
}
