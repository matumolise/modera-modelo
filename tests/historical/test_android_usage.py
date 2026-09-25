import unittest

from datetime import datetime, timedelta, timezone

from historical.contracts import ObservationStatus, Provenance
from historical.daily_usage import (
    PreparedInteractiveDurationWindow,
    ScreenStateEvent,
    ScreenStateEventType,
)
from historical.android_usage import (
    AndroidCollectorRunSummary,
    RawAndroidUsageEvent,
    has_continuous_query_coverage,
    map_screen_state_event,
    DailyCaptureEvidence,
    evaluate_daily_capture_evidence,
    build_daily_use_observation_from_android,
    build_daily_use_observation_from_raw_android,
)

UTC = timezone.utc


class RawAndroidUsageEventTests(unittest.TestCase):
    def test_screen_interactive_is_mapped_preserving_event_time(self) -> None:
        raw = RawAndroidUsageEvent(
            schema_version="raw-usage-event-v1",
            collector_run_id="run-1",
            query_begin_epoch_ms=1_756_694_400_000,
            query_end_epoch_ms=1_756_780_800_000,
            collected_at_epoch_ms=1_756_780_900_000,
            event_time_epoch_ms=1_756_730_400_000,
            event_type_code=15,
            event_type_name="SCREEN_INTERACTIVE",
            query_ordinal=4,
        )

        mapped = map_screen_state_event(raw)

        self.assertIsNotNone(mapped)
        self.assertEqual(
            mapped.event_type,
            ScreenStateEventType.INTERACTIVE,
        )
        self.assertEqual(mapped.occurred_at.tzinfo, UTC)
        self.assertEqual(
            int(mapped.occurred_at.timestamp() * 1000),
            raw.event_time_epoch_ms,
        )

    def test_screen_non_interactive_is_mapped(self) -> None:
        raw = RawAndroidUsageEvent(
            schema_version="raw-usage-event-v1",
            collector_run_id="run-1",
            query_begin_epoch_ms=1_756_694_400_000,
            query_end_epoch_ms=1_756_780_800_000,
            collected_at_epoch_ms=1_756_780_900_000,
            event_time_epoch_ms=1_756_732_200_000,
            event_type_code=16,
            event_type_name="SCREEN_NON_INTERACTIVE",
            query_ordinal=5,
        )

        mapped = map_screen_state_event(raw)

        self.assertIsNotNone(mapped)
        self.assertEqual(
            mapped.event_type,
            ScreenStateEventType.NON_INTERACTIVE,
        )

    def test_unrelated_android_event_is_not_mapped(self) -> None:
        raw = RawAndroidUsageEvent(
            schema_version="raw-usage-event-v1",
            collector_run_id="run-1",
            query_begin_epoch_ms=1_756_694_400_000,
            query_end_epoch_ms=1_756_780_800_000,
            collected_at_epoch_ms=1_756_780_900_000,
            event_time_epoch_ms=1_756_730_400_000,
            event_type_code=1,
            event_type_name="ACTIVITY_RESUMED",
            query_ordinal=6,
        )

        self.assertIsNone(map_screen_state_event(raw))

class AndroidCollectorRunSummaryTests(unittest.TestCase):
    def test_successful_empty_query_is_still_a_successful_query(self) -> None:
        summary = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=1000,
            requested_end_epoch_ms=2000,
            collected_at_epoch_ms=3000,
            usage_access_available=True,
            query_returned_null=False,
            event_count=0,
            error_code=None,
            error_message=None,
        )

        self.assertTrue(summary.query_succeeded)

    def test_missing_usage_access_is_not_a_successful_query(self) -> None:
        summary = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=1000,
            requested_end_epoch_ms=2000,
            collected_at_epoch_ms=3000,
            usage_access_available=False,
            query_returned_null=False,
            event_count=0,
            error_code="USAGE_ACCESS_NOT_GRANTED",
            error_message="Usage Access no disponible.",
        )

        self.assertFalse(summary.query_succeeded)

    def test_null_query_is_not_a_successful_query(self) -> None:
        summary = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=1000,
            requested_end_epoch_ms=2000,
            collected_at_epoch_ms=3000,
            usage_access_available=True,
            query_returned_null=True,
            event_count=0,
            error_code="QUERY_RETURNED_NULL",
            error_message="La consulta devolvió null.",
        )

        self.assertFalse(summary.query_succeeded)

    def test_single_successful_run_can_cover_target_interval(self) -> None:
        run = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=500,
            requested_end_epoch_ms=2500,
            collected_at_epoch_ms=3000,
            usage_access_available=True,
            query_returned_null=False,
            event_count=0,
            error_code=None,
            error_message=None,
        )

        self.assertTrue(
            has_continuous_query_coverage(
                summaries=[run],
                target_begin_epoch_ms=1000,
                target_end_epoch_ms=2000,
            )
        )


    def test_overlapping_successful_runs_can_jointly_cover_target_interval(self) -> None:
        runs = [
            AndroidCollectorRunSummary(
                collector_run_id="run-1",
                requested_begin_epoch_ms=1000,
                requested_end_epoch_ms=1600,
                collected_at_epoch_ms=1700,
                usage_access_available=True,
                query_returned_null=False,
                event_count=1,
                error_code=None,
                error_message=None,
            ),
            AndroidCollectorRunSummary(
                collector_run_id="run-2",
                requested_begin_epoch_ms=1500,
                requested_end_epoch_ms=2000,
                collected_at_epoch_ms=2100,
                usage_access_available=True,
                query_returned_null=False,
                event_count=1,
                error_code=None,
                error_message=None,
            ),
        ]

        self.assertTrue(
            has_continuous_query_coverage(
                summaries=runs,
                target_begin_epoch_ms=1000,
                target_end_epoch_ms=2000,
            )
        )


    def test_gap_between_runs_does_not_count_as_complete_coverage(self) -> None:
        runs = [
            AndroidCollectorRunSummary(
                collector_run_id="run-1",
                requested_begin_epoch_ms=1000,
                requested_end_epoch_ms=1400,
                collected_at_epoch_ms=1500,
                usage_access_available=True,
                query_returned_null=False,
                event_count=1,
                error_code=None,
                error_message=None,
            ),
            AndroidCollectorRunSummary(
                collector_run_id="run-2",
                requested_begin_epoch_ms=1500,
                requested_end_epoch_ms=2000,
                collected_at_epoch_ms=2100,
                usage_access_available=True,
                query_returned_null=False,
                event_count=1,
                error_code=None,
                error_message=None,
            ),
        ]

        self.assertFalse(
            has_continuous_query_coverage(
                summaries=runs,
                target_begin_epoch_ms=1000,
                target_end_epoch_ms=2000,
            )
        )


    def test_failed_run_does_not_provide_query_coverage(self) -> None:
        run = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=1000,
            requested_end_epoch_ms=2000,
            collected_at_epoch_ms=2100,
            usage_access_available=False,
            query_returned_null=False,
            event_count=0,
            error_code="USAGE_ACCESS_NOT_GRANTED",
            error_message="Usage Access no disponible.",
        )

        self.assertFalse(
            has_continuous_query_coverage(
                summaries=[run],
                target_begin_epoch_ms=1000,
                target_end_epoch_ms=2000,
            )
        )

class DailyCaptureEvidenceTests(unittest.TestCase):
    def test_evidence_is_sufficient_only_when_both_conditions_hold(self) -> None:
        evidence = DailyCaptureEvidence(
            continuous_query_coverage=True,
            initial_state_known=True,
        )

        self.assertTrue(evidence.sufficient_for_reconstruction)

    def test_continuous_coverage_without_initial_state_is_not_sufficient(self) -> None:
        evidence = DailyCaptureEvidence(
            continuous_query_coverage=True,
            initial_state_known=False,
        )

        self.assertFalse(evidence.sufficient_for_reconstruction)

    def test_initial_state_without_continuous_coverage_is_not_sufficient(self) -> None:
        evidence = DailyCaptureEvidence(
            continuous_query_coverage=False,
            initial_state_known=True,
        )

        self.assertFalse(evidence.sufficient_for_reconstruction)

class AndroidDailyObservationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.interval_start = datetime(
            2026, 9, 25, 0, 0, tzinfo=timezone.utc
        )
        self.interval_end = datetime(
            2026, 9, 26, 0, 0, tzinfo=timezone.utc
        )

        self.provenance = Provenance(
            source_id="android-usage-events",
            source_version="raw-usage-event-v1",
            source_semantics="SCREEN_INTERACTIVE_SCREEN_NON_INTERACTIVE",
            adapter_version="android-daily-use-v1",
            input_fingerprint="test-input",
        )

    def _successful_full_day_summary(self) -> AndroidCollectorRunSummary:
        return AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=int(
                self.interval_start.timestamp() * 1000
            ),
            requested_end_epoch_ms=int(
                self.interval_end.timestamp() * 1000
            ),
            collected_at_epoch_ms=int(
                (self.interval_end + timedelta(minutes=1)).timestamp() * 1000
            ),
            usage_access_available=True,
            query_returned_null=False,
            event_count=2,
            error_code=None,
            error_message=None,
        )

    def test_sufficient_capture_builds_observed_daily_duration(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=self.interval_start - timedelta(minutes=30),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=self.interval_start + timedelta(hours=1),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=self.interval_start + timedelta(hours=2),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        observation = build_daily_use_observation_from_android(
            observation_id="obs-1",
            subject_id="subject-1",
            interval_start=self.interval_start,
            interval_end=self.interval_end,
            computed_at=self.interval_end + timedelta(minutes=2),
            events=events,
            summaries=[self._successful_full_day_summary()],
            provenance=self.provenance,
        )

        self.assertEqual(observation.status, ObservationStatus.OBSERVED)
        self.assertEqual(observation.value, 60.0)

    def test_missing_initial_state_builds_missing_observation(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=self.interval_start + timedelta(hours=1),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=self.interval_start + timedelta(hours=2),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        observation = build_daily_use_observation_from_android(
            observation_id="obs-2",
            subject_id="subject-1",
            interval_start=self.interval_start,
            interval_end=self.interval_end,
            computed_at=self.interval_end + timedelta(minutes=2),
            events=events,
            summaries=[self._successful_full_day_summary()],
            provenance=self.provenance,
        )

        self.assertEqual(observation.status, ObservationStatus.MISSING)
        self.assertIsNone(observation.value)

    def test_incomplete_query_coverage_builds_missing_observation(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=self.interval_start - timedelta(minutes=30),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        partial_summary = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=int(
                self.interval_start.timestamp() * 1000
            ),
            requested_end_epoch_ms=int(
                (self.interval_start + timedelta(hours=12)).timestamp() * 1000
            ),
            collected_at_epoch_ms=int(
                (self.interval_start + timedelta(hours=12, minutes=1))
                .timestamp() * 1000
            ),
            usage_access_available=True,
            query_returned_null=False,
            event_count=0,
            error_code=None,
            error_message=None,
        )

        observation = build_daily_use_observation_from_android(
            observation_id="obs-3",
            subject_id="subject-1",
            interval_start=self.interval_start,
            interval_end=self.interval_end,
            computed_at=self.interval_end + timedelta(minutes=2),
            events=events,
            summaries=[partial_summary],
            provenance=self.provenance,
        )

        self.assertEqual(observation.status, ObservationStatus.MISSING)
        self.assertIsNone(observation.value)

    def test_raw_android_events_can_build_daily_observation(self) -> None:
        interval_start_ms = int(self.interval_start.timestamp() * 1000)
        interval_end_ms = int(self.interval_end.timestamp() * 1000)

        raw_events = [
            RawAndroidUsageEvent(
                schema_version="raw-usage-event-v1",
                collector_run_id="run-1",
                query_begin_epoch_ms=interval_start_ms - 3600000,
                query_end_epoch_ms=interval_end_ms,
                collected_at_epoch_ms=interval_end_ms + 60000,
                event_time_epoch_ms=interval_start_ms - 1800000,
                event_type_code=16,
                event_type_name="SCREEN_NON_INTERACTIVE",
                query_ordinal=0,
            ),
            RawAndroidUsageEvent(
                schema_version="raw-usage-event-v1",
                collector_run_id="run-1",
                query_begin_epoch_ms=interval_start_ms - 3600000,
                query_end_epoch_ms=interval_end_ms,
                collected_at_epoch_ms=interval_end_ms + 60000,
                event_time_epoch_ms=interval_start_ms + 3600000,
                event_type_code=15,
                event_type_name="SCREEN_INTERACTIVE",
                query_ordinal=0,
            ),
            RawAndroidUsageEvent(
                schema_version="raw-usage-event-v1",
                collector_run_id="run-1",
                query_begin_epoch_ms=interval_start_ms - 3600000,
                query_end_epoch_ms=interval_end_ms,
                collected_at_epoch_ms=interval_end_ms + 60000,
                event_time_epoch_ms=interval_start_ms + 7200000,
                event_type_code=16,
                event_type_name="SCREEN_NON_INTERACTIVE",
                query_ordinal=1,
            ),
        ]

        summary = AndroidCollectorRunSummary(
            collector_run_id="run-1",
            requested_begin_epoch_ms=interval_start_ms - 3600000,
            requested_end_epoch_ms=interval_end_ms,
            collected_at_epoch_ms=interval_end_ms + 60000,
            usage_access_available=True,
            query_returned_null=False,
            event_count=3,
            error_code=None,
            error_message=None,
        )

        observation = build_daily_use_observation_from_raw_android(
            observation_id="obs-raw-1",
            subject_id="subject-1",
            interval_start=self.interval_start,
            interval_end=self.interval_end,
            computed_at=self.interval_end + timedelta(minutes=2),
            raw_events=raw_events,
            summaries=[summary],
            provenance=self.provenance,
        )

        self.assertEqual(observation.status, ObservationStatus.OBSERVED)
        self.assertEqual(observation.value, 60.0)

    def test_raw_event_without_matching_summary_is_rejected(self) -> None:
        interval_start_ms = int(self.interval_start.timestamp() * 1000)
        interval_end_ms = int(self.interval_end.timestamp() * 1000)

        raw_event = RawAndroidUsageEvent(
            schema_version="raw-usage-event-v1",
            collector_run_id="run-desconocido",
            query_begin_epoch_ms=interval_start_ms,
            query_end_epoch_ms=interval_end_ms,
            collected_at_epoch_ms=interval_end_ms + 60000,
            event_time_epoch_ms=interval_start_ms + 3600000,
            event_type_code=15,
            event_type_name="SCREEN_INTERACTIVE",
            query_ordinal=0,
        )

        with self.assertRaisesRegex(
            ValueError,
            "collector run",
        ):
            build_daily_use_observation_from_raw_android(
                observation_id="obs-raw-inconsistente",
                subject_id="child-1",
                interval_start=self.interval_start,
                interval_end=self.interval_end,
                computed_at=self.interval_end + timedelta(minutes=1),
                raw_events=[raw_event],
                summaries=[self._successful_full_day_summary()],
                provenance=self.provenance,
            )
