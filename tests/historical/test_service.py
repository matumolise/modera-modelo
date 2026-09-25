import unittest

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from historical import (
    C1DetectorConfig,
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.persistence import (
    FileHistoricalRepository,
    HistoricalStreamKey,
)
from historical.service import process_c1_representation


UTC = timezone.utc


def representation(
    day: int,
    value: float,
    *,
    record_id: str | None = None,
) -> HistoricalRepresentation:
    start = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=day)

    return HistoricalRepresentation(
        representation_record_id=record_id or f"service-rep-{day}",
        representation_spec_id="daily-use-minutes.v1",
        subject_id="child-001",
        phenomenon="DAILY_TOTAL_USE",
        interval_start=start,
        interval_end=start + timedelta(days=1),
        value=value,
        unit="minutes",
        status=ObservationStatus.OBSERVED,
        coverage=Coverage(),
        provenance=Provenance(source_id="f14-service-test"),
        computed_at=start + timedelta(days=1),
    )


class HistoricalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )

        self.stream_key = HistoricalStreamKey.from_c1(
            subject_id="child-001",
            representation_spec_id="daily-use-minutes.v1",
            config=self.config,
            analysis_version="historical_analyzer_v1",
        )

    def process(
        self,
        repository: FileHistoricalRepository,
        current: HistoricalRepresentation,
        suffix: str,
    ):
        return process_c1_representation(
            repository=repository,
            current=current,
            stream_key=self.stream_key,
            config=self.config,
            evaluation_id=f"eval-{suffix}",
            event_id=f"event-{suffix}",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=current.interval_end,
            emitted_at=current.interval_end,
        )

    def test_new_representation_is_analyzed_and_persisted(self) -> None:
        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            result = self.process(
                repository,
                representation(0, 90.0),
                "001",
            )

            history = repository.load_history(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
            )

            self.assertEqual(len(history), 1)
            self.assertEqual(
                history[0].representation_record_id,
                "service-rep-0",
            )
            self.assertEqual(
                repository.load_state(self.stream_key),
                result.next_state,
            )

    def test_duplicate_is_rejected_without_advancing_state(self) -> None:
        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            current = representation(0, 90.0)

            first = self.process(
                repository,
                current,
                "001",
            )

            with self.assertRaisesRegex(
                ValueError,
                "ya fue procesada",
            ):
                self.process(
                    repository,
                    current,
                    "002",
                )

            self.assertEqual(
                repository.load_state(self.stream_key),
                first.next_state,
            )

            history = repository.load_history(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
            )
            self.assertEqual(len(history), 1)

    def test_out_of_order_representation_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            self.process(
                repository,
                representation(2, 110.0),
                "001",
            )

            with self.assertRaisesRegex(
                ValueError,
                "orden temporal",
            ):
                self.process(
                    repository,
                    representation(1, 100.0),
                    "002",
                )

            history = repository.load_history(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
            )
            self.assertEqual(len(history), 1)

    def test_temporal_gap_is_allowed(self) -> None:
        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            self.process(
                repository,
                representation(0, 90.0),
                "001",
            )
            result = self.process(
                repository,
                representation(3, 120.0),
                "002",
            )

            history = repository.load_history(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
            )

            self.assertEqual(len(history), 2)
            self.assertEqual(
                history[-1].representation_record_id,
                "service-rep-3",
            )
            self.assertEqual(
                repository.load_state(self.stream_key),
                result.next_state,
            )

    def test_incompatible_stream_is_rejected_without_persisting(self) -> None:
        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical.json"
            )

            incompatible_key = HistoricalStreamKey.from_c1(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
                config=C1DetectorConfig(
                    k=1.0,
                    threshold=3.0,
                    min_history=3,
                ),
                analysis_version="historical_analyzer_v1",
            )

            with self.assertRaisesRegex(
                ValueError,
                "no coincide",
            ):
                process_c1_representation(
                    repository=repository,
                    current=representation(0, 90.0),
                    stream_key=incompatible_key,
                    config=self.config,
                    evaluation_id="eval-incompatible",
                    event_id="event-incompatible",
                    analysis_version="historical_analyzer_v1",
                    emitter_version="historical_emitter_v1",
                    computed_at=datetime(
                        2026,
                        9,
                        2,
                        tzinfo=UTC,
                    ),
                    emitted_at=datetime(
                        2026,
                        9,
                        2,
                        tzinfo=UTC,
                    ),
                )

            history = repository.load_history(
                subject_id="child-001",
                representation_spec_id="daily-use-minutes.v1",
            )

            self.assertEqual(history, [])
            self.assertFalse(
                repository.contains_representation(
                    "service-rep-0"
                )
            )


if __name__ == "__main__":
    unittest.main()
