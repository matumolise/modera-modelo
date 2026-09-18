import unittest
from datetime import datetime, timedelta, timezone

from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.reference import MAD_NORMAL_CONSISTENCY, build_scalar_reference


UTC = timezone.utc


def representation(
    day: int,
    value,
    *,
    status: ObservationStatus = ObservationStatus.OBSERVED,
    subject_id: str = "child-001",
    spec_id: str = "total_use.daily_minutes.v1",
    phenomenon: str = "TOTAL_USE_MINUTES",
    unit: str | None = "minutes",
    record_id: str | None = None,
) -> HistoricalRepresentation:
    start = datetime(2026, 9, day, tzinfo=UTC)
    return HistoricalRepresentation(
        representation_record_id=record_id or f"rep-{day}",
        representation_spec_id=spec_id,
        subject_id=subject_id,
        phenomenon=phenomenon,
        interval_start=start,
        interval_end=start + timedelta(days=1),
        value=value,
        unit=unit,
        status=status,
        coverage=Coverage(value=None, basis="temporal"),
        quality_flags=(),
        provenance=Provenance(source_id="test"),
        computed_at=start + timedelta(days=1, hours=1),
    )


class ScalarReferenceTests(unittest.TestCase):
    def test_current_observation_never_enters_its_own_reference(self) -> None:
        previous = representation(14, 10.0)
        current = representation(15, 1000.0)

        reference = build_scalar_reference(current, [previous, current])

        self.assertEqual(reference.history_count, 1)
        self.assertEqual(reference.location, 10.0)

    def test_future_observation_cannot_change_past_reference(self) -> None:
        previous = [
            representation(12, 10.0),
            representation(13, 20.0),
            representation(14, 30.0),
        ]
        current = representation(15, 40.0)
        future = representation(16, 10000.0)

        without_future = build_scalar_reference(current, previous)
        with_future = build_scalar_reference(current, [*previous, future])

        self.assertEqual(with_future, without_future)

    def test_future_unrelated_observation_cannot_change_past_reference(self) -> None:
        previous = [
            representation(12, 10.0),
            representation(13, 20.0),
            representation(14, 30.0),
        ]
        current = representation(15, 40.0)
        future_unrelated = representation(
            16,
            10000.0,
            subject_id="child-999",
            spec_id="other.v1",
        )

        without_future = build_scalar_reference(current, previous)
        with_future = build_scalar_reference(
            current,
            [*previous, future_unrelated],
        )

        self.assertEqual(with_future, without_future)

    def test_reference_uses_median_and_scaled_mad(self) -> None:
        history = [
            representation(12, 0.0, status=ObservationStatus.OBSERVED_ZERO),
            representation(13, 2.0),
            representation(14, 4.0),
        ]
        current = representation(15, 5.0)

        reference = build_scalar_reference(current, history)

        self.assertEqual(reference.location, 2.0)
        self.assertAlmostEqual(
            reference.scale,
            MAD_NORMAL_CONSISTENCY * 2.0,
            places=12,
        )
        self.assertTrue(reference.estimable)

    def test_missing_and_not_applicable_do_not_contribute(self) -> None:
        history = [
            representation(11, None, status=ObservationStatus.MISSING),
            representation(12, None, status=ObservationStatus.NOT_APPLICABLE),
            representation(13, 10.0),
            representation(14, 20.0),
        ]
        current = representation(15, 30.0)

        reference = build_scalar_reference(current, history)

        self.assertEqual(reference.history_count, 2)
        self.assertEqual(reference.location, 15.0)

    def test_constant_history_is_non_estimable(self) -> None:
        history = [
            representation(12, 3.0),
            representation(13, 3.0),
            representation(14, 3.0),
        ]
        current = representation(15, 4.0)

        reference = build_scalar_reference(current, history)

        self.assertEqual(reference.location, 3.0)
        self.assertEqual(reference.scale, 0.0)
        self.assertFalse(reference.estimable)

    def test_empty_usable_history_is_non_estimable_without_inventing_values(self) -> None:
        current = representation(15, 4.0)

        reference = build_scalar_reference(current, [])

        self.assertEqual(reference.history_count, 0)
        self.assertIsNone(reference.location)
        self.assertIsNone(reference.scale)
        self.assertFalse(reference.estimable)

    def test_reference_cutoff_is_current_interval_start(self) -> None:
        current = representation(15, 4.0)

        reference = build_scalar_reference(current, [representation(14, 3.0)])

        self.assertEqual(reference.reference_cutoff, current.interval_start)

    def test_same_history_different_order_same_result(self) -> None:
        history = [
            representation(12, 10.0),
            representation(13, 30.0),
            representation(14, 20.0),
        ]
        current = representation(15, 40.0)

        forward = build_scalar_reference(current, history)
        reverse = build_scalar_reference(current, list(reversed(history)))

        self.assertEqual(forward, reverse)

    def test_mixed_subject_history_is_rejected(self) -> None:
        current = representation(15, 40.0)
        wrong_subject = representation(14, 20.0, subject_id="child-999")

        with self.assertRaises(ValueError):
            build_scalar_reference(current, [wrong_subject])

    def test_mixed_representation_spec_history_is_rejected(self) -> None:
        current = representation(15, 40.0)
        wrong_spec = representation(14, 20.0, spec_id="other.v1")

        with self.assertRaises(ValueError):
            build_scalar_reference(current, [wrong_spec])

    def test_structured_values_are_not_silently_coerced_to_scalar(self) -> None:
        current = representation(15, 40.0)
        structured = representation(14, {"games": 0.5, "education": 0.5})

        with self.assertRaises(TypeError):
            build_scalar_reference(current, [structured])


if __name__ == "__main__":
    unittest.main()
