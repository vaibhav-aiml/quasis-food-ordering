package com.quasis.foodordering

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.quasis.foodordering.accessibility.FoodAccessibilityService
import com.quasis.foodordering.engine.OrderOrchestrator
import com.quasis.foodordering.models.ExecutionStatusDto
import com.quasis.foodordering.network.BackendApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Main Launcher Activity for Quasis Food Ordering Assistant.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var cardAccessibility: MaterialCardView
    private lateinit var tvAccessibilityStatus: TextView
    private lateinit var tvAccessibilityDesc: TextView
    private lateinit var btnEnableAccessibility: Button

    private lateinit var etServerUrl: EditText
    private lateinit var etOrderPrompt: EditText
    private lateinit var btnOrderWithAgent: Button

    private lateinit var chipPizza: Chip
    private lateinit var chipBiryani: Chip
    private lateinit var chipDosa: Chip

    private lateinit var cardProgress: MaterialCardView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvProgressTitle: TextView
    private lateinit var tvProgressLogs: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        setupListeners()
    }

    override fun onResume() {
        super.onResume()
        updateAccessibilityStatus()
    }

    private fun initViews() {
        cardAccessibility = findViewById(R.id.cardAccessibility)
        tvAccessibilityStatus = findViewById(R.id.tvAccessibilityStatus)
        tvAccessibilityDesc = findViewById(R.id.tvAccessibilityDesc)
        btnEnableAccessibility = findViewById(R.id.btnEnableAccessibility)

        etServerUrl = findViewById(R.id.etServerUrl)
        etOrderPrompt = findViewById(R.id.etOrderPrompt)
        btnOrderWithAgent = findViewById(R.id.btnOrderWithAgent)

        chipPizza = findViewById(R.id.chipPizza)
        chipBiryani = findViewById(R.id.chipBiryani)
        chipDosa = findViewById(R.id.chipDosa)

        cardProgress = findViewById(R.id.cardProgress)
        progressBar = findViewById(R.id.progressBar)
        tvProgressTitle = findViewById(R.id.tvProgressTitle)
        tvProgressLogs = findViewById(R.id.tvProgressLogs)
    }

    private fun setupListeners() {
        btnEnableAccessibility.setOnClickListener {
            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            startActivity(intent)
        }

        chipPizza.setOnClickListener {
            etOrderPrompt.setText("Order Margherita Pizza from Domino's on Swiggy")
        }

        chipBiryani.setOnClickListener {
            etOrderPrompt.setText("Order chicken biryani from Meghana Foods with extra raita")
        }

        chipDosa.setOnClickListener {
            etOrderPrompt.setText("Order 2 masala dosa from Saravana Bhavan")
        }

        btnOrderWithAgent.setOnClickListener {
            val prompt = etOrderPrompt.text.toString().trim()
            if (prompt.isEmpty()) {
                Toast.makeText(this, "Please enter what you would like to order", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (!FoodAccessibilityService.isRunning()) {
                Toast.makeText(this, "Please enable Accessibility Service first", Toast.LENGTH_LONG).show()
                val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                startActivity(intent)
                return@setOnClickListener
            }

            startAgentOrderFlow(prompt)
        }
    }

    private fun updateAccessibilityStatus() {
        val isRunning = FoodAccessibilityService.isRunning()
        if (isRunning) {
            cardAccessibility.setCardBackgroundColor(Color.parseColor("#E8F5E9"))
            cardAccessibility.strokeColor = Color.parseColor("#60B246")
            tvAccessibilityStatus.text = "✅ Accessibility Service Active"
            tvAccessibilityStatus.setTextColor(Color.parseColor("#2E7D32"))
            tvAccessibilityDesc.text = "Ready to automate Swiggy food ordering on your phone."
            btnEnableAccessibility.visibility = View.GONE
        } else {
            cardAccessibility.setCardBackgroundColor(Color.parseColor("#FFF8E1"))
            cardAccessibility.strokeColor = Color.parseColor("#FFA726")
            tvAccessibilityStatus.text = "⚠️ Accessibility Service Disabled"
            tvAccessibilityStatus.setTextColor(Color.parseColor("#E65100"))
            tvAccessibilityDesc.text = "Tap below to enable Accessibility for Quasis in Settings."
            btnEnableAccessibility.visibility = View.VISIBLE
        }
    }

    private fun startAgentOrderFlow(prompt: String) {
        var serverUrl = etServerUrl.text.toString().trim()
        if (serverUrl.isEmpty()) {
            serverUrl = "http://192.168.1.5:8008"
        }
        if (!serverUrl.startsWith("http://") && !serverUrl.startsWith("https://")) {
            serverUrl = "http://$serverUrl"
        }
        // Remove duplicate protocol prefixes if user pasted
        while (serverUrl.contains("http://http://") || serverUrl.contains("http://https://")) {
            serverUrl = serverUrl.replace("http://http://", "http://").replace("http://https://", "https://")
        }
        serverUrl = serverUrl.trimEnd('/')

        val client = BackendApiClient(baseUrl = serverUrl)

        cardProgress.visibility = View.VISIBLE
        progressBar.visibility = View.VISIBLE
        tvProgressTitle.text = "🤖 AI Agent Thinking..."
        tvProgressLogs.text = "Connecting to backend at $serverUrl...\nParsing request: \"$prompt\""
        btnOrderWithAgent.isEnabled = false

        // Listen for live step changes during automation
        OrderOrchestrator.stateChangeListener = { state ->
            lifecycleScope.launch(Dispatchers.Main) {
                val stepLog = buildString {
                    appendLine("Execution Plan ID: ${state.plan_id}")
                    appendLine("Current Step: ${state.current_step_id}")
                    appendLine("Status: ${state.status}")
                    state.completed_steps.forEach { step ->
                        appendLine("✓ Step ${step.step_id} (${step.step_type}): ${step.message ?: "Done"}")
                    }
                    if (state.error_message != null) {
                        appendLine("❌ Error: ${state.error_message}")
                    }
                }
                tvProgressLogs.text = stepLog

                if (state.status == ExecutionStatusDto.READY_FOR_PAYMENT || state.ready_for_payment) {
                    progressBar.visibility = View.GONE
                    tvProgressTitle.text = "🎉 Ready for Payment!"
                    tvProgressTitle.setTextColor(Color.parseColor("#2E7D32"))
                    btnOrderWithAgent.isEnabled = true
                    Toast.makeText(this@MainActivity, "Items added to cart! Please review and pay.", Toast.LENGTH_LONG).show()
                } else if (state.status == ExecutionStatusDto.FAILED) {
                    progressBar.visibility = View.GONE
                    tvProgressTitle.text = "❌ Order Failed"
                    tvProgressTitle.setTextColor(Color.parseColor("#E53935"))
                    btnOrderWithAgent.isEnabled = true
                }
            }
        }

        lifecycleScope.launch(Dispatchers.IO) {
            val result = client.createOrderPlan(prompt)
            withContext(Dispatchers.Main) {
                result.fold(
                    onSuccess = { plan ->
                        tvProgressTitle.text = "🚀 Executing Swiggy Automation..."
                        tvProgressLogs.text = "Plan compiled successfully (${plan.steps.size} steps)\nStarting Android UI automation..."

                        // Trigger orchestrator with compiled plan
                        OrderOrchestrator.startExecution(plan)
                    },
                    onFailure = { error ->
                        progressBar.visibility = View.GONE
                        tvProgressTitle.text = "❌ Failed to create plan"
                        tvProgressTitle.setTextColor(Color.parseColor("#E53935"))
                        tvProgressLogs.text = "Error communicating with backend: ${error.message}\n\nPlease check server URL and ensure backend is running."
                        btnOrderWithAgent.isEnabled = true
                    }
                )
            }
        }
    }
}
