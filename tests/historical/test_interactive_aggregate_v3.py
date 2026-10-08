"""Validación del contrato diario recibido desde Android, sin conectarlo a C1."""

import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from historical.contracts import ObservationStatus
from historical.interactive_aggregate_v3 import (
    AndroidInteractiveAggregateV3, InitialStateV3, QueryWindowV3,
    INTERACTIVE_SCREEN_SPEC_ID_V3, adapt_interactive_aggregate_v3,
    review_aggregate_v3,
)
from historical.interactive_duration_v3 import ALGORITHM_VERSION


def fixture(**changes):
    zone = ZoneInfo("America/Argentina/Buenos_Aires")
    start = datetime(2026, 10, 5, tzinfo=zone)
    end = datetime(2026, 10, 6, tzinfo=zone)
    begin_ms = round(start.timestamp() * 1000)
    end_ms = round(end.timestamp() * 1000)
    fields = dict(
        capture_id="run-day-1", device_id="device-pseudonym-1",
        local_date=date(2026, 10, 5), time_zone_id="America/Argentina/Buenos_Aires",
        interval_start=start, interval_end=end,
        computed_at=datetime(2026, 10, 6, 4, tzinfo=timezone.utc),
        algorithm_version=ALGORITHM_VERSION,
        status=ObservationStatus.OBSERVED, interactive_screen_minutes=120.0,
        missing_reason=None, initial_state=InitialStateV3(begin_ms - 60000, 16),
        query_windows=(QueryWindowV3("q1", begin_ms - 120000, end_ms, True),),
        restart_in_day=False, conflicting_overlaps=False,
        ambiguous_event_order=False,
    )
    fields.update(changes)
    return AndroidInteractiveAggregateV3(**fields)


class AggregateContractV3Tests(unittest.TestCase):
    def test_isolated_device_stream_and_status(self):
        result = adapt_interactive_aggregate_v3(fixture(), representation_record_id="r1")
        self.assertEqual(result.representation_spec_id, INTERACTIVE_SCREEN_SPEC_ID_V3)
        self.assertEqual(result.subject_id, "device-pseudonym-1")
        self.assertEqual(result.value, 120.0)
        self.assertIn("DEVICE_LEVEL_ONLY", result.quality_flags)
        self.assertIsNone(result.coverage.value)

    def test_zero_requires_capture_and_preserves_zero_status(self):
        source = fixture(status=ObservationStatus.OBSERVED_ZERO,
                         interactive_screen_minutes=0.0)
        self.assertEqual(review_aggregate_v3(source)[:2],
                         (ObservationStatus.OBSERVED_ZERO, 0.0))
        no_state = replace(source, initial_state=None)
        result = adapt_interactive_aggregate_v3(no_state, representation_record_id="r2")
        self.assertEqual(result.status, ObservationStatus.MISSING)
        self.assertIsNone(result.value)

    def test_query_gap_and_failed_query_cannot_support_value(self):
        source = fixture()
        gap = replace(source, query_windows=(replace(source.query_windows[0],
                end_epoch_ms=source.query_windows[0].end_epoch_ms - 60000),))
        self.assertEqual(review_aggregate_v3(gap)[2], "INCOMPLETE_QUERY_COVERAGE")
        failed = replace(source, query_windows=(replace(source.query_windows[0],
                succeeded=False),))
        self.assertEqual(review_aggregate_v3(failed)[0], ObservationStatus.MISSING)

    def test_restarts_conflicts_and_ambiguity_abstain(self):
        for flag, reason in (("restart_in_day", "RESTART_IN_DAY"),
                             ("conflicting_overlaps", "CONFLICTING_OVERLAPPING_QUERIES"),
                             ("ambiguous_event_order", "AMBIGUOUS_EVENT_ORDER")):
            with self.subTest(flag=flag):
                self.assertEqual(review_aggregate_v3(fixture(**{flag: True}))[2], reason)

    def test_missing_and_invalid_numeric_contract(self):
        source = fixture(status=ObservationStatus.MISSING,
                         interactive_screen_minutes=None,
                         missing_reason="PERMISSION_DENIED")
        self.assertEqual(review_aggregate_v3(source),
                         (ObservationStatus.MISSING, None, "PERMISSION_DENIED"))
        for bad in (float("nan"), float("inf"), -1, 1441, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fixture(interactive_screen_minutes=bad)
        with self.assertRaises(ValueError):
            fixture(status=ObservationStatus.OBSERVED_ZERO)

    def test_local_day_and_algorithm_are_strict(self):
        with self.assertRaisesRegex(ValueError, "fecha local"):
            fixture(local_date=date(2026, 10, 4))
        with self.assertRaisesRegex(ValueError, "Versión"):
            fixture(algorithm_version="unknown")
        with self.assertRaisesRegex(ValueError, "Tipos"):
            fixture(status="OBSERVED")
        with self.assertRaisesRegex(ValueError, "Ventana"):
            QueryWindowV3("q", 0, 60, 1)
        with self.assertRaisesRegex(ValueError, "Tipos"):
            fixture(query_windows=[])

    def test_daylight_saving_uses_real_boundaries(self):
        zone = ZoneInfo("Europe/Madrid")
        start = datetime(2026, 10, 25, tzinfo=zone)
        end = datetime(2026, 10, 26, tzinfo=zone)
        self.assertEqual(round((end.timestamp() - start.timestamp()) / 60), 1500)
        begin_ms = round(start.timestamp() * 1000)
        end_ms = round(end.timestamp() * 1000)
        source = fixture(time_zone_id="Europe/Madrid", local_date=date(2026, 10, 25),
                         interval_start=start, interval_end=end,
                         computed_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
                         initial_state=InitialStateV3(begin_ms - 60000, 16),
                         query_windows=(QueryWindowV3("q", begin_ms - 60000,
                                                      end_ms, True),),
                         interactive_screen_minutes=1500.0)
        self.assertEqual(review_aggregate_v3(source)[1], 1500.0)


if __name__ == "__main__":
    unittest.main()
