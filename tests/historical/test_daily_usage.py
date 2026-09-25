import unittest

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from historical.detector import C1DetectorConfig
from historical.persistence import (
    FileHistoricalRepository,
    HistoricalStreamKey,
)
from historical.service import process_c1_representation
from historical.adapters import (
    DAILY_USE_DURATION_SPEC_ID,
    adapt_daily_use_duration,
)
from historical.contracts import ObservationStatus, Provenance
from historical.daily_usage import (
    DailyInteractiveDuration,
    ScreenStateEvent,
    ScreenStateEventType,
    build_daily_use_observation,
    calculate_interactive_duration,
)


UTC = timezone.utc


class ScreenStateEventTests(unittest.TestCase):
    def test_interactive_event_preserves_behavior_time(self) -> None:
        occurred_at = datetime(
            2026,
            9,
            1,
            10,
            30,
            tzinfo=UTC,
        )

        event = ScreenStateEvent(
            occurred_at=occurred_at,
            event_type=ScreenStateEventType.INTERACTIVE,
        )

        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(
            event.event_type,
            ScreenStateEventType.INTERACTIVE,
        )

    def test_naive_behavior_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "zona horaria",
        ):
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 30),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            )

class DailyInteractiveDurationTests(unittest.TestCase):
    def test_closed_interactive_interval_is_accumulated(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 30, tzinfo=UTC),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        result = calculate_interactive_duration(events)

        self.assertEqual(result.duration_minutes, 30.0)
        self.assertFalse(result.has_open_interval)

    def test_multiple_closed_intervals_are_accumulated(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 20, tzinfo=UTC),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 12, 40, tzinfo=UTC),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        result = calculate_interactive_duration(events)

        self.assertEqual(result.duration_minutes, 60.0)
        self.assertFalse(result.has_open_interval)

    def test_open_interval_does_not_invent_duration(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
        ]

        result = calculate_interactive_duration(events)

        self.assertEqual(result.duration_minutes, 0.0)
        self.assertTrue(result.has_open_interval)
    
    def test_negative_duration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no negativo"):
            DailyInteractiveDuration(
                duration_minutes=-1.0,
                has_open_interval=False,
            )

    def test_non_finite_duration_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finito"):
                    DailyInteractiveDuration(
                        duration_minutes=value,
                        has_open_interval=False,
                    )

class DailyUseObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.day_start = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
        self.day_end = datetime(2026, 9, 2, 0, 0, tzinfo=UTC)
        self.computed_at = datetime(2026, 9, 2, 0, 5, tzinfo=UTC)
        self.provenance = Provenance(
            source_id="test-screen-events",
            source_semantics="screen_interactive_intervals",
        )

    def test_complete_closed_capture_becomes_observed(self) -> None:
        reconstruction = DailyInteractiveDuration(
            duration_minutes=30.0,
            has_open_interval=False,
        )

        observation = build_daily_use_observation(
            observation_id="obs-1",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=True,
            provenance=self.provenance,
        )

        self.assertEqual(observation.value, 30.0)
        self.assertEqual(observation.unit, "minutes")
        self.assertEqual(observation.status, ObservationStatus.OBSERVED)

    def test_complete_zero_capture_becomes_observed_zero(self) -> None:
        reconstruction = DailyInteractiveDuration(
            duration_minutes=0.0,
            has_open_interval=False,
        )

        observation = build_daily_use_observation(
            observation_id="obs-2",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=True,
            provenance=self.provenance,
        )

        self.assertEqual(observation.value, 0.0)
        self.assertEqual(
            observation.status,
            ObservationStatus.OBSERVED_ZERO,
        )

    def test_incomplete_capture_becomes_missing(self) -> None:
        reconstruction = DailyInteractiveDuration(
            duration_minutes=30.0,
            has_open_interval=False,
        )

        observation = build_daily_use_observation(
            observation_id="obs-3",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=False,
            provenance=self.provenance,
        )

        self.assertIsNone(observation.value)
        self.assertEqual(observation.status, ObservationStatus.MISSING)

    def test_open_interval_becomes_missing_even_when_capture_is_complete(self) -> None:
        reconstruction = DailyInteractiveDuration(
            duration_minutes=30.0,
            has_open_interval=True,
        )

        observation = build_daily_use_observation(
            observation_id="obs-4",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=True,
            provenance=self.provenance,
        )

        self.assertIsNone(observation.value)
        self.assertEqual(observation.status, ObservationStatus.MISSING)
    
    def test_complete_capture_reaches_historical_representation(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 30, tzinfo=UTC),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        reconstruction = calculate_interactive_duration(events)

        observation = build_daily_use_observation(
            observation_id="obs-integration-1",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=True,
            provenance=self.provenance,
        )

        representation = adapt_daily_use_duration(
            observation,
            representation_record_id="rep-integration-1",
        )

        self.assertEqual(representation.value, 30.0)
        self.assertEqual(
            representation.status,
            ObservationStatus.OBSERVED,
        )
        self.assertEqual(
            representation.representation_spec_id,
            DAILY_USE_DURATION_SPEC_ID,
        )
        self.assertEqual(representation.subject_id, "subject-1")
    
    def test_complete_capture_is_processed_and_persisted(self) -> None:
        events = [
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_type=ScreenStateEventType.INTERACTIVE,
            ),
            ScreenStateEvent(
                occurred_at=datetime(2026, 9, 1, 10, 30, tzinfo=UTC),
                event_type=ScreenStateEventType.NON_INTERACTIVE,
            ),
        ]

        reconstruction = calculate_interactive_duration(events)

        observation = build_daily_use_observation(
            observation_id="obs-e2e-1",
            subject_id="subject-1",
            interval_start=self.day_start,
            interval_end=self.day_end,
            computed_at=self.computed_at,
            reconstruction=reconstruction,
            capture_complete=True,
            provenance=self.provenance,
        )

        representation = adapt_daily_use_duration(
            observation,
            representation_record_id="rep-e2e-1",
        )

        config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )

        stream_key = HistoricalStreamKey.from_c1(
            subject_id="subject-1",
            representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            config=config,
            analysis_version="historical_analyzer_v1",
        )

        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            result = process_c1_representation(
                repository=repository,
                current=representation,
                stream_key=stream_key,
                config=config,
                evaluation_id="eval-e2e-1",
                event_id="event-e2e-1",
                analysis_version="historical_analyzer_v1",
                emitter_version="historical_emitter_v1",
                computed_at=self.computed_at,
                emitted_at=self.computed_at,
            )

            history = repository.load_history(
                subject_id="subject-1",
                representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
            )

            self.assertEqual(len(history), 1)
            self.assertEqual(
                history[0].representation_record_id,
                "rep-e2e-1",
            )
            self.assertEqual(history[0].value, 30.0)
            self.assertEqual(
                repository.load_state(stream_key),
                result.next_state,
            )

if __name__ == "__main__":
    unittest.main()