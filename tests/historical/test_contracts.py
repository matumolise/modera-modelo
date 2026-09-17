import unittest
from datetime import datetime, timedelta, timezone

from historical.contracts import (
    BehavioralObservation,
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)


UTC = timezone.utc


def aware(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


class CoverageTests(unittest.TestCase):
    def test_unknown_coverage_is_not_assumed_full(self) -> None:
        coverage = Coverage(value=None, basis="temporal")

        self.assertFalse(coverage.is_known)
        self.assertFalse(coverage.is_full)

    def test_coverage_preserves_basis(self) -> None:
        coverage = Coverage(value=0.8, basis="temporal")

        self.assertEqual(coverage.value, 0.8)
        self.assertEqual(coverage.basis, "temporal")

    def test_coverage_rejects_values_outside_zero_one(self) -> None:
        with self.assertRaises(ValueError):
            Coverage(value=1.01, basis="temporal")


class BehavioralObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = aware(2026, 9, 16)
        self.end = self.start + timedelta(days=1)
        self.computed_at = aware(2026, 9, 17, 12)
        self.provenance = Provenance(
            source_id="android_usage_events",
            source_version=None,
            source_semantics="Events recovered from Android UsageEvents.",
            adapter_version="android-adapter-v0",
        )

    def make_observation(self, **overrides):
        values = {
            "observation_id": "obs-001",
            "subject_id": "child-001",
            "interval_start": self.start,
            "interval_end": self.end,
            "phenomenon": "TOTAL_USE_MINUTES",
            "value": 120.0,
            "unit": "minutes",
            "status": ObservationStatus.OBSERVED,
            "coverage": Coverage(value=None, basis="temporal"),
            "quality_flags": (),
            "provenance": self.provenance,
            "computed_at": self.computed_at,
        }
        values.update(overrides)
        return BehavioralObservation(**values)

    def test_observed_zero_is_not_missing(self) -> None:
        observation = self.make_observation(
            value=0.0,
            status=ObservationStatus.OBSERVED_ZERO,
        )

        self.assertEqual(observation.value, 0.0)
        self.assertEqual(observation.status, ObservationStatus.OBSERVED_ZERO)
        self.assertNotEqual(observation.status, ObservationStatus.MISSING)

    def test_missing_never_accepts_a_numeric_value(self) -> None:
        with self.assertRaises(ValueError):
            self.make_observation(
                value=0.0,
                status=ObservationStatus.MISSING,
            )

    def test_not_applicable_is_not_zero(self) -> None:
        observation = self.make_observation(
            value=None,
            status=ObservationStatus.NOT_APPLICABLE,
        )

        self.assertIsNone(observation.value)
        self.assertEqual(
            observation.status,
            ObservationStatus.NOT_APPLICABLE,
        )

    def test_scalar_zero_must_use_observed_zero(self) -> None:
        with self.assertRaises(ValueError):
            self.make_observation(
                value=0.0,
                status=ObservationStatus.OBSERVED,
            )

    def test_structured_value_with_zero_component_remains_observed(self) -> None:
        observation = self.make_observation(
            phenomenon="APP_CATEGORY_COMPOSITION",
            value={"games": 0.0, "education": 1.0},
            unit="share",
            status=ObservationStatus.OBSERVED,
        )

        self.assertEqual(observation.status, ObservationStatus.OBSERVED)

    def test_processing_time_does_not_change_behavior_interval(self) -> None:
        observation = self.make_observation()

        self.assertEqual(observation.interval_start, self.start)
        self.assertEqual(observation.interval_end, self.end)
        self.assertEqual(observation.computed_at, self.computed_at)
        self.assertGreater(observation.computed_at, observation.interval_end)

    def test_naive_timestamps_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.make_observation(
                interval_start=datetime(2026, 9, 16),
            )


class HistoricalRepresentationTests(unittest.TestCase):
    def test_record_identity_is_separate_from_spec_identity(self) -> None:
        start = aware(2026, 9, 16)
        representation = HistoricalRepresentation(
            representation_record_id="rep-record-001",
            representation_spec_id="total_use.daily_minutes.v1",
            subject_id="child-001",
            phenomenon="TOTAL_USE_MINUTES",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=120.0,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(value=1.0, basis="temporal"),
            quality_flags=(),
            provenance=Provenance(
                source_id="behavioral_observation",
                adapter_version="historical-representation-v1",
            ),
            computed_at=start + timedelta(days=1, hours=1),
        )

        self.assertEqual(
            representation.representation_record_id,
            "rep-record-001",
        )
        self.assertEqual(
            representation.representation_spec_id,
            "total_use.daily_minutes.v1",
        )
        self.assertNotEqual(
            representation.representation_record_id,
            representation.representation_spec_id,
        )


if __name__ == "__main__":
    unittest.main()
