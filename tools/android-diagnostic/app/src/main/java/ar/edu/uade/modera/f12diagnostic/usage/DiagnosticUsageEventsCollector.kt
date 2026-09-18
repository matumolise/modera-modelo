package ar.edu.uade.modera.f12diagnostic.usage

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Build
import android.os.Process
import java.util.UUID

data class RawUsageEventRecordV1(
    val schemaVersion: String = "raw-usage-event-v1",
    val collectorRunId: String,
    val queryBeginEpochMs: Long,
    val queryEndEpochMs: Long,
    val collectedAtEpochMs: Long,
    val eventTimeEpochMs: Long,
    val eventTypeCode: Int,
    val eventTypeName: String,
    val packageName: String?,
    val className: String?,
    val androidApiLevel: Int,
    val manufacturer: String,
    val model: String,
    val queryOrdinal: Int,
)

data class CollectorRunSummary(
    val collectorRunId: String,
    val requestedBeginEpochMs: Long,
    val requestedEndEpochMs: Long,
    val collectedAtEpochMs: Long,
    val usageAccessAvailable: Boolean,
    val queryReturnedNull: Boolean,
    val eventCount: Int,
    val errorCode: String?,
    val errorMessage: String?,
)

data class UsageEventsCollectionResult(
    val summary: CollectorRunSummary,
    val events: List<RawUsageEventRecordV1>,
)

class DiagnosticUsageEventsCollector(
    context: Context,
) {
    private val appContext = context.applicationContext
    private val usageStatsManager = requireNotNull(
        appContext.getSystemService(UsageStatsManager::class.java),
    )
    private val appOpsManager = requireNotNull(
        appContext.getSystemService(AppOpsManager::class.java),
    )

    fun hasUsageAccess(): Boolean {
        val mode = appOpsManager.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            Process.myUid(),
            appContext.packageName,
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    fun collect(
        beginTimeEpochMs: Long,
        endTimeEpochMs: Long,
    ): UsageEventsCollectionResult {
        require(beginTimeEpochMs < endTimeEpochMs) {
            "beginTimeEpochMs must be before endTimeEpochMs"
        }

        val collectorRunId = UUID.randomUUID().toString()
        val collectedAt = System.currentTimeMillis()
        val accessAvailable = hasUsageAccess()

        if (!accessAvailable) {
            return resultWithError(
                collectorRunId = collectorRunId,
                beginTimeEpochMs = beginTimeEpochMs,
                endTimeEpochMs = endTimeEpochMs,
                collectedAt = collectedAt,
                usageAccessAvailable = false,
                errorCode = "USAGE_ACCESS_NOT_GRANTED",
                errorMessage = "Usage Access is not granted for this app.",
            )
        }

        return try {
            val usageEvents: UsageEvents? =
                usageStatsManager.queryEvents(beginTimeEpochMs, endTimeEpochMs)

            if (usageEvents == null) {
                UsageEventsCollectionResult(
                    summary = CollectorRunSummary(
                        collectorRunId = collectorRunId,
                        requestedBeginEpochMs = beginTimeEpochMs,
                        requestedEndEpochMs = endTimeEpochMs,
                        collectedAtEpochMs = collectedAt,
                        usageAccessAvailable = true,
                        queryReturnedNull = true,
                        eventCount = 0,
                        errorCode = "QUERY_RETURNED_NULL",
                        errorMessage = "UsageStatsManager.queryEvents returned null.",
                    ),
                    events = emptyList(),
                )
            } else {
                collectFromQuery(
                    usageEvents = usageEvents,
                    collectorRunId = collectorRunId,
                    beginTimeEpochMs = beginTimeEpochMs,
                    endTimeEpochMs = endTimeEpochMs,
                    collectedAt = collectedAt,
                )
            }
        } catch (exception: SecurityException) {
            resultWithError(
                collectorRunId = collectorRunId,
                beginTimeEpochMs = beginTimeEpochMs,
                endTimeEpochMs = endTimeEpochMs,
                collectedAt = collectedAt,
                usageAccessAvailable = accessAvailable,
                errorCode = "SECURITY_EXCEPTION",
                errorMessage = exception.message,
            )
        } catch (exception: RuntimeException) {
            resultWithError(
                collectorRunId = collectorRunId,
                beginTimeEpochMs = beginTimeEpochMs,
                endTimeEpochMs = endTimeEpochMs,
                collectedAt = collectedAt,
                usageAccessAvailable = accessAvailable,
                errorCode = "QUERY_RUNTIME_EXCEPTION",
                errorMessage = exception.message,
            )
        }
    }

    private fun collectFromQuery(
        usageEvents: UsageEvents,
        collectorRunId: String,
        beginTimeEpochMs: Long,
        endTimeEpochMs: Long,
        collectedAt: Long,
    ): UsageEventsCollectionResult {
        val records = mutableListOf<RawUsageEventRecordV1>()
        val event = UsageEvents.Event()
        var ordinal = 0

        while (usageEvents.hasNextEvent()) {
            if (!usageEvents.getNextEvent(event)) {
                break
            }

            records += RawUsageEventRecordV1(
                collectorRunId = collectorRunId,
                queryBeginEpochMs = beginTimeEpochMs,
                queryEndEpochMs = endTimeEpochMs,
                collectedAtEpochMs = collectedAt,
                eventTimeEpochMs = event.timeStamp,
                eventTypeCode = event.eventType,
                eventTypeName = eventTypeName(event.eventType),
                packageName = event.packageName,
                className = event.className,
                androidApiLevel = Build.VERSION.SDK_INT,
                manufacturer = Build.MANUFACTURER,
                model = Build.MODEL,
                queryOrdinal = ordinal,
            )
            ordinal += 1
        }

        val orderedRecords = records.sortedWith(
            compareBy<RawUsageEventRecordV1> { it.eventTimeEpochMs }
                .thenBy { it.queryOrdinal },
        )

        return UsageEventsCollectionResult(
            summary = CollectorRunSummary(
                collectorRunId = collectorRunId,
                requestedBeginEpochMs = beginTimeEpochMs,
                requestedEndEpochMs = endTimeEpochMs,
                collectedAtEpochMs = collectedAt,
                usageAccessAvailable = true,
                queryReturnedNull = false,
                eventCount = orderedRecords.size,
                errorCode = null,
                errorMessage = null,
            ),
            events = orderedRecords,
        )
    }

    private fun resultWithError(
        collectorRunId: String,
        beginTimeEpochMs: Long,
        endTimeEpochMs: Long,
        collectedAt: Long,
        usageAccessAvailable: Boolean,
        errorCode: String,
        errorMessage: String?,
    ): UsageEventsCollectionResult =
        UsageEventsCollectionResult(
            summary = CollectorRunSummary(
                collectorRunId = collectorRunId,
                requestedBeginEpochMs = beginTimeEpochMs,
                requestedEndEpochMs = endTimeEpochMs,
                collectedAtEpochMs = collectedAt,
                usageAccessAvailable = usageAccessAvailable,
                queryReturnedNull = false,
                eventCount = 0,
                errorCode = errorCode,
                errorMessage = errorMessage,
            ),
            events = emptyList(),
        )

    @Suppress("DEPRECATION")
    private fun eventTypeName(eventType: Int): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return when (eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> "ACTIVITY_RESUMED"
                UsageEvents.Event.ACTIVITY_PAUSED -> "ACTIVITY_PAUSED"
                UsageEvents.Event.ACTIVITY_STOPPED -> "ACTIVITY_STOPPED"
                UsageEvents.Event.FOREGROUND_SERVICE_START -> "FOREGROUND_SERVICE_START"
                UsageEvents.Event.FOREGROUND_SERVICE_STOP -> "FOREGROUND_SERVICE_STOP"
                UsageEvents.Event.DEVICE_STARTUP -> "DEVICE_STARTUP"
                UsageEvents.Event.DEVICE_SHUTDOWN -> "DEVICE_SHUTDOWN"
                UsageEvents.Event.CONFIGURATION_CHANGE -> "CONFIGURATION_CHANGE"
                UsageEvents.Event.USER_INTERACTION -> "USER_INTERACTION"
                UsageEvents.Event.SHORTCUT_INVOCATION -> "SHORTCUT_INVOCATION"
                UsageEvents.Event.STANDBY_BUCKET_CHANGED -> "STANDBY_BUCKET_CHANGED"
                UsageEvents.Event.SCREEN_INTERACTIVE -> "SCREEN_INTERACTIVE"
                UsageEvents.Event.SCREEN_NON_INTERACTIVE -> "SCREEN_NON_INTERACTIVE"
                UsageEvents.Event.KEYGUARD_SHOWN -> "KEYGUARD_SHOWN"
                UsageEvents.Event.KEYGUARD_HIDDEN -> "KEYGUARD_HIDDEN"
                UsageEvents.Event.NONE -> "NONE"
                else -> "EVENT_TYPE_$eventType"
            }
        }

        return when (eventType) {
            UsageEvents.Event.SCREEN_INTERACTIVE -> "SCREEN_INTERACTIVE"
            UsageEvents.Event.SCREEN_NON_INTERACTIVE -> "SCREEN_NON_INTERACTIVE"
            UsageEvents.Event.KEYGUARD_SHOWN -> "KEYGUARD_SHOWN"
            UsageEvents.Event.KEYGUARD_HIDDEN -> "KEYGUARD_HIDDEN"
            UsageEvents.Event.MOVE_TO_FOREGROUND -> "MOVE_TO_FOREGROUND"
            UsageEvents.Event.MOVE_TO_BACKGROUND -> "MOVE_TO_BACKGROUND"
            UsageEvents.Event.CONFIGURATION_CHANGE -> "CONFIGURATION_CHANGE"
            UsageEvents.Event.USER_INTERACTION -> "USER_INTERACTION"
            UsageEvents.Event.SHORTCUT_INVOCATION -> "SHORTCUT_INVOCATION"
            UsageEvents.Event.STANDBY_BUCKET_CHANGED -> "STANDBY_BUCKET_CHANGED"
            UsageEvents.Event.NONE -> "NONE"
            else -> "EVENT_TYPE_$eventType"
        }
    }
}
