package ar.edu.uade.modera.f12diagnostic.usage

import org.junit.Assert.assertEquals
import org.junit.Test

class UsageEventTypeNameMapperTest {

    @Test
    fun modernApiUsesModernActivityAndServiceNames() {
        val apiLevel = 29

        assertEquals(
            "ACTIVITY_RESUMED",
            UsageEventTypeNameMapper.nameFor(1, apiLevel),
        )
        assertEquals(
            "ACTIVITY_PAUSED",
            UsageEventTypeNameMapper.nameFor(2, apiLevel),
        )
        assertEquals(
            "STANDBY_BUCKET_CHANGED",
            UsageEventTypeNameMapper.nameFor(11, apiLevel),
        )
        assertEquals(
            "EVENT_TYPE_12",
            UsageEventTypeNameMapper.nameFor(12, apiLevel),
        )
        assertEquals(
            "FOREGROUND_SERVICE_START",
            UsageEventTypeNameMapper.nameFor(19, apiLevel),
        )
        assertEquals(
            "FOREGROUND_SERVICE_STOP",
            UsageEventTypeNameMapper.nameFor(20, apiLevel),
        )
    }

    @Test
    fun api28UsesLegacyForegroundBackgroundNames() {
        val apiLevel = 28

        assertEquals(
            "MOVE_TO_FOREGROUND",
            UsageEventTypeNameMapper.nameFor(1, apiLevel),
        )
        assertEquals(
            "MOVE_TO_BACKGROUND",
            UsageEventTypeNameMapper.nameFor(2, apiLevel),
        )
    }

    @Test
    fun unknownEventTypeFallsBackWithoutInventingSemantics() {
        assertEquals(
            "EVENT_TYPE_999",
            UsageEventTypeNameMapper.nameFor(999, 37),
        )
    }
}
