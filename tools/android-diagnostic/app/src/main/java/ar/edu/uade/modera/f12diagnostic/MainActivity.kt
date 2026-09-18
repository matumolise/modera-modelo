package ar.edu.uade.modera.f12diagnostic

import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import ar.edu.uade.modera.f12diagnostic.export.DiagnosticExport
import ar.edu.uade.modera.f12diagnostic.usage.DiagnosticUsageEventsCollector

class MainActivity : AppCompatActivity() {

    private lateinit var collector: DiagnosticUsageEventsCollector
    private lateinit var exporter: DiagnosticExport
    private lateinit var accessStatusText: TextView
    private lateinit var collectionStatusText: TextView
    private lateinit var collectButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        collector = DiagnosticUsageEventsCollector(this)
        exporter = DiagnosticExport(this)
        accessStatusText = findViewById(R.id.accessStatusText)
        collectionStatusText = findViewById(R.id.collectionStatusText)
        collectButton = findViewById(R.id.collectButton)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        findViewById<Button>(R.id.openUsageAccessButton).setOnClickListener {
            openUsageAccessSettings()
        }

        collectButton.setOnClickListener {
            collectLastHour()
        }
    }

    override fun onResume() {
        super.onResume()
        refreshUsageAccessStatus()
    }

    private fun refreshUsageAccessStatus() {
        val granted = collector.hasUsageAccess()
        accessStatusText.text = if (granted) {
            getString(R.string.usage_access_granted)
        } else {
            getString(R.string.usage_access_missing)
        }
        collectButton.isEnabled = granted
    }

    private fun openUsageAccessSettings() {
        try {
            startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(
                this,
                R.string.usage_access_settings_unavailable,
                Toast.LENGTH_LONG,
            ).show()
        }
    }

    private fun collectLastHour() {
        collectButton.isEnabled = false
        collectionStatusText.setText(R.string.collecting)

        Thread {
            val endTime = System.currentTimeMillis()
            val beginTime = endTime - ONE_HOUR_MS

            val message = try {
                val result = collector.collect(beginTime, endTime)

                if (result.summary.errorCode != null) {
                    getString(
                        R.string.collection_failed,
                        result.summary.errorCode,
                        result.summary.errorMessage.orEmpty(),
                    )
                } else {
                    val exported = exporter.export(result)
                    getString(
                        R.string.collection_succeeded,
                        result.summary.eventCount,
                        result.summary.collectorRunId,
                        exported.directory.absolutePath,
                    )
                }
            } catch (exception: Exception) {
                getString(
                    R.string.collection_failed,
                    exception::class.java.simpleName,
                    exception.message.orEmpty(),
                )
            }

            runOnUiThread {
                collectionStatusText.text = message
                refreshUsageAccessStatus()
            }
        }.start()
    }

    companion object {
        private const val ONE_HOUR_MS = 60L * 60L * 1000L
    }
}