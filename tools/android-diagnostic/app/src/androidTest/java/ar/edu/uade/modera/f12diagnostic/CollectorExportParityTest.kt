package ar.edu.uade.modera.f12diagnostic

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import android.app.Instrumentation
import android.os.Bundle
import ar.edu.uade.modera.f12diagnostic.export.DiagnosticExport
import ar.edu.uade.modera.f12diagnostic.usage.DiagnosticUsageEventsCollector
import ar.edu.uade.modera.f12diagnostic.usage.UsageEventsCollectionResult
import java.io.File
import java.security.MessageDigest
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.util.TimeZone
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Harness diagnóstico: consulta explícita, export original y referencia local.
 * No prueba exhaustividad del SO ni atribución personal. No altera la UI.
 */
@RunWith(AndroidJUnit4::class)
class CollectorExportParityTest {
    @Test
    fun exportExplicitWindow() {
        val args = InstrumentationRegistry.getArguments()
        fun required(name: String): String = requireNotNull(args.getString(name)) {
            "Missing instrumentation argument: $name"
        }
        val queryBegin = required("f12BeginEpochMs").toLong()
        val queryEnd = required("f12EndEpochMs").toLong()
        val day = LocalDate.parse(required("f12LocalDate"))
        val zone = ZoneId.of(required("f12TimeZone"))
        val startLocal = day.atTime(LocalTime.MIDNIGHT)
        val endLocal = day.plusDays(1).atTime(LocalTime.MIDNIGHT)
        require(zone.rules.getValidOffsets(startLocal).size == 1)
        require(zone.rules.getValidOffsets(endLocal).size == 1)
        val begin = startLocal.atZone(zone).toInstant().toEpochMilli()
        val end = endLocal.atZone(zone).toInstant().toEpochMilli()
        require(queryBegin < queryEnd && queryEnd <= System.currentTimeMillis() && end <= System.currentTimeMillis()) {
            "A closed local day and a nonempty query are required"
        }
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val result = DiagnosticUsageEventsCollector(context).collect(queryBegin, queryEnd)
        // La UI no exporta errores: el harness sí, sin modificar DiagnosticExport.
        val exported = DiagnosticExport(context).export(result)
        InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
            putString(Instrumentation.REPORT_KEY_STREAMRESULT,
                "F12_EXPORT_RUN=${result.summary.collectorRunId}\nF12_EXPORT_DIRECTORY=${exported.directory.absolutePath}\n")
        })
        val summary = JSONObject(exported.summaryFile.readText(Charsets.UTF_8))
        val rows = exported.eventsFile.readLines(Charsets.UTF_8)
        assertEquals(result.summary.eventCount, rows.size)
        assertEquals(result.summary.collectorRunId, summary.getString("collectorRunId"))
        rows.forEachIndexed { index, line ->
            val row = JSONObject(line)
            assertEquals(14, row.length())
            assertEquals(result.events[index].queryOrdinal, row.getInt("queryOrdinal"))
            assertEquals(result.events[index].eventTimeEpochMs, row.getLong("eventTimeEpochMs"))
        }
        assertEquals(9, summary.length())
        val reference = reference(result, begin, end)
        val report = JSONObject().apply {
            put("reportSchema", "f12-phone-parity-v1")
            put("collectorRunId", result.summary.collectorRunId)
            put("summarySha256", hash(exported.summaryFile))
            put("eventsSha256", hash(exported.eventsFile))
            put("localDate", day.toString())
            put("timeZone", zone.id)
            put("phoneTimeZone", TimeZone.getDefault().id)
            put("intervalBeginEpochMs", begin)
            put("intervalEndEpochMs", end)
            put("status", reference.first)
            put("durationMs", reference.second ?: JSONObject.NULL)
            put("manualCaptureValidation", "PENDING")
        }
        val safeId = result.summary.collectorRunId.replace("-", "")
        val reportFile = File(exported.directory, "parity_$safeId.json")
        assertTrue(reportFile.createNewFile())
        reportFile.writeText(report.toString(2), Charsets.UTF_8)
        InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
            putString(Instrumentation.REPORT_KEY_STREAMRESULT, "F12_PARITY_REPORT=${reportFile.absolutePath}\n")
        })
    }

    private fun hash(file: File): String = MessageDigest.getInstance("SHA-256")
        .digest(file.readBytes()).joinToString("") { "%02x".format(it.toInt() and 255) }

    /** Reconstrucción independiente, de una consulta; no usa Python ni C1. */
    private fun reference(result: UsageEventsCollectionResult, begin: Long, end: Long): Pair<String, Long?> {
        val summary = result.summary
        val missing = Pair<String, Long?>("MISSING", null)
        if (!summary.usageAccessAvailable || summary.queryReturnedNull || summary.errorCode != null
            || summary.collectedAtEpochMs < summary.requestedEndEpochMs) return missing
        val screen = result.events.filter {
            it.eventTypeName == "SCREEN_INTERACTIVE" || it.eventTypeName == "SCREEN_NON_INTERACTIVE"
        }
        screen.groupBy { it.eventTimeEpochMs }.values.forEach { sameTime ->
            require(sameTime.map { it.eventTypeName }.distinct().size == 1) {
                "Contradictory screen states at the same timestamp"
            }
        }
        val prior = screen.lastOrNull { it.eventTimeEpochMs < begin } ?: return missing
        if (summary.requestedBeginEpochMs > prior.eventTimeEpochMs || summary.requestedEndEpochMs < end) return missing
        if (result.events.any {
                it.eventTimeEpochMs >= prior.eventTimeEpochMs && it.eventTimeEpochMs < end &&
                    (it.eventTypeName == "DEVICE_STARTUP" || it.eventTypeName == "DEVICE_SHUTDOWN")
            }) return missing
        var interactive = prior.eventTypeName == "SCREEN_INTERACTIVE"
        var cursor = begin
        var duration = 0L
        screen.filter { it.eventTimeEpochMs >= begin && it.eventTimeEpochMs < end }.forEach {
            if (interactive) duration += it.eventTimeEpochMs - cursor
            cursor = it.eventTimeEpochMs
            interactive = it.eventTypeName == "SCREEN_INTERACTIVE"
        }
        if (interactive) duration += end - cursor
        return Pair(if (duration == 0L) "OBSERVED_ZERO" else "OBSERVED", duration)
    }
}
