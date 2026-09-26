import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from historical import (
    AndroidCollectorRunSummary,
    C1DetectorConfig,
    DAILY_USE_DURATION_SPEC_ID,
    FileHistoricalRepository,
    HistoricalStreamKey,
    ObservationStatus,
    Provenance,
    RawAndroidUsageEvent,
    adapt_daily_use_duration,
    build_daily_use_observation_from_raw_android,
    process_c1_representation,
    DetectionEventDecision,
)


class AndroidHistoricalVerticalTests(unittest.TestCase):
    """Prueba el primer vertical completo desde captura Android hasta persistencia."""

    SUBJECT_ID = "child-test"
    ANALYSIS_VERSION = "f14.7-integration-test-v1"
    EMITTER_VERSION = "f14.7-integration-test-emitter-v1"

    def setUp(self) -> None:
        self.base_day = datetime(
            2026,
            9,
            20,
            tzinfo=timezone.utc,
        )
        self.config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )
        self.stream_key = HistoricalStreamKey.from_c1(
            subject_id=self.SUBJECT_ID,
            representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            config=self.config,
            analysis_version=self.ANALYSIS_VERSION,
        )

    def _build_observation(
        self,
        *,
        day_index: int,
        duration_minutes: int,
        complete_capture: bool = True,
    ):
        interval_start = self.base_day + timedelta(days=day_index)
        interval_end = interval_start + timedelta(days=1)
        query_begin = interval_start - timedelta(hours=1)

        query_begin_ms = int(query_begin.timestamp() * 1000)
        query_end_ms = int(interval_end.timestamp() * 1000)
        run_id = f"run-day-{day_index + 1}"

        def raw_event(
            occurred_at: datetime,
            event_type_name: str,
            ordinal: int,
        ) -> RawAndroidUsageEvent:
            return RawAndroidUsageEvent(
                schema_version="raw-usage-event-v1",
                collector_run_id=run_id,
                query_begin_epoch_ms=query_begin_ms,
                query_end_epoch_ms=query_end_ms,
                collected_at_epoch_ms=query_end_ms + 60000,
                event_time_epoch_ms=int(occurred_at.timestamp() * 1000),
                event_type_code=0,
                event_type_name=event_type_name,
                query_ordinal=ordinal,
            )

        raw_events = [
            raw_event(
                interval_start - timedelta(minutes=30),
                "SCREEN_NON_INTERACTIVE",
                0,
            ),
            raw_event(
                interval_start + timedelta(hours=10),
                "SCREEN_INTERACTIVE",
                1,
            ),
            raw_event(
                interval_start
                + timedelta(
                    hours=10,
                    minutes=duration_minutes,
                ),
                "SCREEN_NON_INTERACTIVE",
                2,
            ),
        ]

        summary = AndroidCollectorRunSummary(
            collector_run_id=run_id,
            requested_begin_epoch_ms=query_begin_ms,
            requested_end_epoch_ms=(
                query_end_ms
                if complete_capture
                else query_end_ms - 3600000
            ),
            collected_at_epoch_ms=query_end_ms + 60000,
            usage_access_available=True,
            query_returned_null=False,
            event_count=len(raw_events),
            error_code=None,
            error_message=None,
        )

        if not complete_capture:
            raw_events = [
                RawAndroidUsageEvent(
                    schema_version=event.schema_version,
                    collector_run_id=event.collector_run_id,
                    query_begin_epoch_ms=event.query_begin_epoch_ms,
                    query_end_epoch_ms=query_end_ms - 3600000,
                    collected_at_epoch_ms=event.collected_at_epoch_ms,
                    event_time_epoch_ms=event.event_time_epoch_ms,
                    event_type_code=event.event_type_code,
                    event_type_name=event.event_type_name,
                    query_ordinal=event.query_ordinal,
                )
                for event in raw_events
            ]

        provenance = Provenance(
            source_id="android-usage-events",
            source_version="raw-usage-event-v1",
            source_semantics=(
                "Duración de pantalla interactiva reportada por Android."
            ),
            input_fingerprint=f"fixture-day-{day_index + 1}",
        )

        return build_daily_use_observation_from_raw_android(
            observation_id=f"obs-day-{day_index + 1}",
            subject_id=self.SUBJECT_ID,
            interval_start=interval_start,
            interval_end=interval_end,
            computed_at=interval_end + timedelta(minutes=1),
            raw_events=raw_events,
            summaries=[summary],
            provenance=provenance,
        )

    def _process_observation(
        self,
        *,
        repository: FileHistoricalRepository,
        observation,
        day_index: int,
    ):
        representation = adapt_daily_use_duration(
            observation,
            representation_record_id=f"rep-day-{day_index + 1}",
        )

        return process_c1_representation(
            repository=repository,
            current=representation,
            stream_key=self.stream_key,
            config=self.config,
            evaluation_id=f"evaluation-day-{day_index + 1}",
            event_id=f"event-day-{day_index + 1}",
            analysis_version=self.ANALYSIS_VERSION,
            emitter_version=self.EMITTER_VERSION,
            computed_at=observation.interval_end + timedelta(minutes=2),
            emitted_at=observation.interval_end + timedelta(minutes=3),
        )

    def test_raw_android_day_reaches_historical_analyzer_and_persistence(
        self,
    ) -> None:
        observation = self._build_observation(
            day_index=0,
            duration_minutes=60,
        )

        self.assertEqual(
            observation.status,
            ObservationStatus.OBSERVED,
        )
        self.assertEqual(observation.value, 60.0)

        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = FileHistoricalRepository(
                Path(temporary_directory)
                / "historical-repository.json"
            )

            result = self._process_observation(
                repository=repository,
                observation=observation,
                day_index=0,
            )

            self.assertEqual(
                result.evaluation.representation_record_id,
                "rep-day-1",
            )

            persisted_history = repository.load_history(
                subject_id=self.SUBJECT_ID,
                representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            )

            self.assertEqual(len(persisted_history), 1)
            self.assertEqual(
                persisted_history[0].representation_record_id,
                "rep-day-1",
            )
            self.assertEqual(
                persisted_history[0].value,
                60.0,
            )

    def test_missing_day_and_analyzer_state_survive_repository_restart(
        self,
    ) -> None:
        observations = [
            self._build_observation(
                day_index=0,
                duration_minutes=60,
            ),
            self._build_observation(
                day_index=1,
                duration_minutes=70,
            ),
            self._build_observation(
                day_index=2,
                duration_minutes=80,
                complete_capture=False,
            ),
            self._build_observation(
                day_index=3,
                duration_minutes=65,
            ),
        ]

        self.assertEqual(
            observations[2].status,
            ObservationStatus.MISSING,
        )
        self.assertIsNone(observations[2].value)

        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_path = (
                Path(temporary_directory)
                / "historical-repository.json"
            )
            repository = FileHistoricalRepository(repository_path)

            for day_index, observation in enumerate(observations):
                self._process_observation(
                    repository=repository,
                    observation=observation,
                    day_index=day_index,
                )

            state_before_restart = repository.load_state(
                self.stream_key
            )

            repository = FileHistoricalRepository(repository_path)

            state_after_restart = repository.load_state(
                self.stream_key
            )

            self.assertEqual(
                state_after_restart,
                state_before_restart,
            )

            day_five = self._build_observation(
                day_index=4,
                duration_minutes=75,
            )

            self._process_observation(
                repository=repository,
                observation=day_five,
                day_index=4,
            )

            persisted_history = repository.load_history(
                subject_id=self.SUBJECT_ID,
                representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            )

            self.assertEqual(len(persisted_history), 5)
            self.assertEqual(
                persisted_history[2].status,
                ObservationStatus.MISSING,
            )
            self.assertIsNone(persisted_history[2].value)

            usable_values = [
                representation.value
                for representation in persisted_history
                if representation.status
                in {
                    ObservationStatus.OBSERVED,
                    ObservationStatus.OBSERVED_ZERO,
                }
            ]

            self.assertEqual(
                usable_values,
                [60.0, 70.0, 65.0, 75.0],
            )

    def test_mature_history_can_emit_technical_detection_event(
        self,
    ) -> None:
        durations = [60, 70, 80, 75, 150]

        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = FileHistoricalRepository(
                Path(temporary_directory)
                / "historical-repository.json"
            )

            results = []

            for day_index, duration_minutes in enumerate(durations):
                observation = self._build_observation(
                    day_index=day_index,
                    duration_minutes=duration_minutes,
                )

                result = self._process_observation(
                    repository=repository,
                    observation=observation,
                    day_index=day_index,
                )
                results.append(result)

            day_four = results[3]
            day_five = results[4]

            self.assertLess(
                day_four.evaluation.detector_statistic,
                self.config.threshold,
            )
            self.assertEqual(
                day_four.emission.decision,
                DetectionEventDecision.NO_EMIT,
            )
            self.assertIsNone(day_four.emission.event)

            self.assertGreaterEqual(
                day_five.evaluation.detector_statistic,
                self.config.threshold,
            )
            self.assertEqual(
                day_five.emission.decision,
                DetectionEventDecision.EMIT,
            )
            self.assertIsNotNone(day_five.emission.event)

            self.assertEqual(
                day_five.emission.event.representation_record_id,
                "rep-day-5",
            )

            persisted_history = repository.load_history(
                subject_id=self.SUBJECT_ID,
                representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            )

            self.assertEqual(len(persisted_history), 5)
            self.assertEqual(
                [item.value for item in persisted_history],
                [60.0, 70.0, 80.0, 75.0, 150.0],
            )

if __name__ == "__main__":
    unittest.main()
