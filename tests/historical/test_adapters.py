import unittest
from datetime import datetime, timezone

from historical import (
    BehavioralObservation,
    Coverage,
    ObservationStatus,
    Provenance,
)
from historical.adapters import (
    DAILY_USE_DURATION_SPEC_ID,
    DAILY_USE_DURATION_PHENOMENON,
    adapt_daily_use_duration,
)


UTC = timezone.utc


def observation(
    value,
    status=ObservationStatus.OBSERVED,
) -> BehavioralObservation:
    return BehavioralObservation(
        observation_id="obs-001",
        subject_id="child-001",
        interval_start=datetime(2026, 9, 1, tzinfo=UTC),
        interval_end=datetime(2026, 9, 2, tzinfo=UTC),
        phenomenon=DAILY_USE_DURATION_PHENOMENON,
        value=value,
        unit="minutes",
        status=status,
        coverage=Coverage(value=0.95, basis="temporal"),
        quality_flags=("delayed_collection",),
        provenance=Provenance(
            source_id="android_usage_capture",
            source_version="v1",
        ),
        computed_at=datetime(2026, 9, 2, 0, 5, tzinfo=UTC),
    )


class DailyUseDurationAdapterTests(unittest.TestCase):
    def test_preserves_semantics_and_traceability(self) -> None:
        source = observation(180.0)

        result = adapt_daily_use_duration(
            source,
            representation_record_id="rep-001",
        )

        self.assertEqual(
            result.representation_spec_id,
            DAILY_USE_DURATION_SPEC_ID,
        )
        self.assertEqual(result.subject_id, source.subject_id)
        self.assertEqual(result.phenomenon, source.phenomenon)
        self.assertEqual(result.interval_start, source.interval_start)
        self.assertEqual(result.interval_end, source.interval_end)
        self.assertEqual(result.value, 180.0)
        self.assertEqual(result.unit, "minutes")
        self.assertEqual(result.status, ObservationStatus.OBSERVED)
        self.assertEqual(result.coverage, source.coverage)
        self.assertEqual(result.quality_flags, source.quality_flags)
        self.assertEqual(result.computed_at, source.computed_at)
        self.assertEqual(
            result.provenance.source_id,
            source.provenance.source_id,
        )

    def test_observed_zero_remains_observed_zero(self) -> None:
        source = observation(
            0.0,
            status=ObservationStatus.OBSERVED_ZERO,
        )

        result = adapt_daily_use_duration(
            source,
            representation_record_id="rep-002",
        )

        self.assertEqual(result.value, 0.0)
        self.assertEqual(
            result.status,
            ObservationStatus.OBSERVED_ZERO,
        )

    def test_missing_remains_missing_instead_of_becoming_zero(self) -> None:
        source = observation(
            None,
            status=ObservationStatus.MISSING,
        )

        result = adapt_daily_use_duration(
            source,
            representation_record_id="rep-003",
        )

        self.assertIsNone(result.value)
        self.assertEqual(result.status, ObservationStatus.MISSING)

    def test_rejects_another_phenomenon(self) -> None:
        source = observation(180.0)

        source = BehavioralObservation(
            observation_id=source.observation_id,
            subject_id=source.subject_id,
            interval_start=source.interval_start,
            interval_end=source.interval_end,
            phenomenon="OTHER_PHENOMENON",
            value=source.value,
            unit=source.unit,
            status=source.status,
            coverage=source.coverage,
            quality_flags=source.quality_flags,
            provenance=source.provenance,
            computed_at=source.computed_at,
        )

        with self.assertRaises(ValueError):
            adapt_daily_use_duration(
                source,
                representation_record_id="rep-004",
            )


    def test_rejects_unit_other_than_minutes(self) -> None:
        source = observation(180.0)

        source = BehavioralObservation(
            observation_id=source.observation_id,
            subject_id=source.subject_id,
            interval_start=source.interval_start,
            interval_end=source.interval_end,
            phenomenon=source.phenomenon,
            value=source.value,
            unit="seconds",
            status=source.status,
            coverage=source.coverage,
            quality_flags=source.quality_flags,
            provenance=source.provenance,
            computed_at=source.computed_at,
        )

        with self.assertRaises(ValueError):
            adapt_daily_use_duration(
                source,
                representation_record_id="rep-005",
            )

if __name__ == "__main__":
    unittest.main()

