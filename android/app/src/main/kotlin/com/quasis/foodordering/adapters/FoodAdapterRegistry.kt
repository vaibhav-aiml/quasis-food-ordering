package com.quasis.foodordering.adapters

/**
 * Registry mapping app identifier string to corresponding FoodAppAdapter implementation.
 */
object FoodAdapterRegistry {

    private val adapters = mutableMapOf<String, FoodAppAdapter>()

    init {
        val swiggy = SwiggyAdapter()
        register(swiggy)
    }

    fun register(adapter: FoodAppAdapter) {
        adapters[adapter.appId.lowercase()] = adapter
        adapters[adapter.appName.lowercase()] = adapter
    }

    fun getAdapter(appNameOrId: String): FoodAppAdapter? {
        return adapters[appNameOrId.trim().lowercase()]
    }

    fun supportedApps(): List<String> = adapters.keys.toList()
}

