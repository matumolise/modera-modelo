package ar.edu.uade.modera.f12diagnostic.export

import android.content.Context
import ar.edu.uade.modera.f12diagnostic.usage.CollectorRunSummary
import ar.edu.uade.modera.f12diagnostic.usage.RawUsageEventRecordV1
import ar.edu.uade.modera.f12diagnostic.usage.UsageEventsCollectionResult
import java.io.File
import org.json.JSONObject

data class ExportedDiagnosticFiles(
    val directory: File,
    val summaryFile: File,
    val eventsFile: File,
)

class DiagnosticExport(
    context: Context,
) {
    private val appContext = context.applicationContext

    fun export(result: UsageEventsCollectionResult): ExportedDiagnosticFiles {
        val root = appContext.getExternalFilesDir(null) ?: appContext.filesDir
        val directory = File(root, "f12-diagnostic")
        check(directory.exists() || directory.mkdirs()) {
            "Could not create diagnostic export directory: ${directory.absolutePath}"
        }

        val safeRunId = result.summary.collectorRunId.replace("-", "")
        val summaryFile = File(directory, "summary_$safeRunId.json")
        val eventsFile = File(directory, "events_$safeRunId.jsonl")

        summaryFile.writeText(
            summaryJson(result.summary).toString(2),
            Charsets.UTF_8,
        )

        eventsFile.bufferedWriter(Charsets.UTF_8).use { writer ->
            result.events.forEach { event ->
                writer.appendLine(eventJson(event).toString())
            }
        }

        return ExportedDiagnosticFiles(
            directory = directory,
            summaryFile = summaryFile,
            eventsFile = eventsFile,
        )
    }

    private fun summaryJson(summary: CollectorRunSummary): JSONObject =
        JSONObject().apply {
            put("collectorRunId", summary.collectorRunId)
            put("requestedBeginEpochMs", summary.requestedBeginEpochMs)
            put("requestedEndEpochMs", summary.requestedEndEpochMs)
            put("collectedAtEpochMs", summary.collectedAtEpochMs)
            put("usageAccessAvailable", summary.usageAccessAvailable)
            put("queryReturnedNull", summary.queryReturnedNull)
            put("eventCount", summary.eventCount)
            putNullable("errorCode", summary.errorCode)
            putNullable("errorMessage", summary.errorMessage)
        }

    private fun eventJson(event: RawUsageEventRecordV1): JSONObject =
        JSONObject().apply {
            put("schemaVersion", event.schemaVersion)
            put("collectorRunId", event.collectorRunId)
            put("queryBeginEpochMs", event.queryBeginEpochMs)
            put("queryEndEpochMs", event.queryEndEpochMs)
            put("collectedAtEpochMs", event.collectedAtEpochMs)
            put("eventTimeEpochMs", event.eventTimeEpochMs)
            put("eventTypeCode", event.eventTypeCode)
            put("eventTypeName", event.eventTypeName)
            putNullable("packageName", event.packageName)
            putNullable("className", event.className)
            put("androidApiLevel", event.androidApiLevel)
            put("manufacturer", event.manufacturer)
            put("model", event.model)
            put("queryOrdinal", event.queryOrdinal)
        }

    private fun JSONObject.putNullable(
        key: String,
        value: String?,
    ) {
        put(key, value ?: JSONObject.NULL)
    }
}
