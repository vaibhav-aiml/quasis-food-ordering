package com.quasis.foodordering.network

import com.quasis.foodordering.models.OrderPlanDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * Lightweight HTTP client for communicating with the Python FastAPI Backend.
 */
class BackendApiClient(
    private val baseUrl: String = "http://10.0.2.2:8000"
) {
    private val jsonParser = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    /**
     * Request the backend to parse user text into a structured intent and OrderPlan.
     */
    suspend fun createOrderPlan(rawText: String): Result<OrderPlanDto> = withContext(Dispatchers.IO) {
        try {
            val endpointUrl = URL("$baseUrl/v1/food/order/plan")
            val connection = endpointUrl.openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            connection.doOutput = true
            connection.connectTimeout = 10000
            connection.readTimeout = 15000

            val requestBody = buildJsonObject {
                put("raw_text", rawText)
            }.toString()

            OutputStreamWriter(connection.outputStream, "UTF-8").use { writer ->
                writer.write(requestBody)
                writer.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode in 200..299) {
                val responseText = BufferedReader(InputStreamReader(connection.inputStream)).use { it.readText() }
                val responseObj = jsonParser.parseToJsonElement(responseText)
                val planObj = responseObj.toString()

                // Extract plan element from FoodPlanResult wrapper
                val planElement = jsonParser.decodeFromString<PlanResultResponse>(planObj)
                if (planElement.plan != null) {
                    Result.success(planElement.plan)
                } else {
                    Result.failure(Exception("Plan could not be generated: ${planElement.status_message}"))
                }
            } else {
                val errorText = BufferedReader(InputStreamReader(connection.errorStream ?: connection.inputStream)).use { it.readText() }
                Result.failure(Exception("HTTP $responseCode: $errorText"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

@kotlinx.serialization.Serializable
private data class PlanResultResponse(
    val ready_to_automate: Boolean = false,
    val status_message: String = "",
    val plan: OrderPlanDto? = null
)
