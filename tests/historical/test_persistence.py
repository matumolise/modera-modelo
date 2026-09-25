import unittest

from datetime import datetime, timedelta, timezone

from historical import C1DetectorConfig
from historical import HistoricalAnalyzerState
from historical.analyzer import analyze_c1_representation
from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.detector import CusumState
from historical.persistence import (
    HistoricalStreamKey,
    deserialize_analyzer_state,
    serialize_analyzer_state,
    FileHistoricalStateStore,
    FileHistoricalRepresentationStore,
    deserialize_historical_representation,
    serialize_historical_representation,
    FileHistoricalRepository,
)

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class HistoricalStreamKeyTests(unittest.TestCase):
    def test_same_identity_and_configuration_produce_same_key(self) -> None:
        config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=7,
        )

        first = HistoricalStreamKey.from_c1(
            subject_id="child-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            config=config,
            analysis_version="historical-c1-v1",
        )
        second = HistoricalStreamKey.from_c1(
            subject_id="child-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            config=config,
            analysis_version="historical-c1-v1",
        )

        self.assertEqual(first, second)

    def test_different_subjects_do_not_share_state(self) -> None:
        config = C1DetectorConfig(0.5, 3.0, 7)

        first = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )
        second = HistoricalStreamKey.from_c1(
            "child-002",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )

        self.assertNotEqual(first, second)

    def test_different_representation_specs_do_not_share_state(self) -> None:
        config = C1DetectorConfig(0.5, 3.0, 7)

        first = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )
        second = HistoricalStreamKey.from_c1(
            "child-001",
            "another_representation_v1",
            config,
            "historical-c1-v1",
        )

        self.assertNotEqual(first, second)

    def test_different_detector_configuration_does_not_share_state(self) -> None:
        first = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            C1DetectorConfig(0.5, 3.0, 7),
            "historical-c1-v1",
        )
        second = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            C1DetectorConfig(1.0, 3.0, 7),
            "historical-c1-v1",
        )

        self.assertNotEqual(first, second)

    def test_different_analysis_versions_do_not_share_state(self) -> None:
        config = C1DetectorConfig(0.5, 3.0, 7)

        first = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )
        second = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v2",
        )

        self.assertNotEqual(first, second)

class HistoricalAnalyzerStateSerializationTests(unittest.TestCase):
    def test_state_round_trip_preserves_cusum_and_previous_statistic(self) -> None:
        state = HistoricalAnalyzerState(
            cusum_state=CusumState(
                positive=2.75,
                negative=0.4,
            ),
            previous_eligible_statistic=2.75,
        )

        payload = serialize_analyzer_state(state)
        restored = deserialize_analyzer_state(payload)

        self.assertEqual(restored, state)

    def test_initial_state_round_trip_preserves_none(self) -> None:
        state = HistoricalAnalyzerState()

        payload = serialize_analyzer_state(state)
        restored = deserialize_analyzer_state(payload)

        self.assertEqual(restored, state)
        self.assertIsNone(restored.previous_eligible_statistic)

class FileHistoricalStateStoreTests(unittest.TestCase):
    def test_saved_state_can_be_loaded_for_same_stream(self) -> None:
        key = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            C1DetectorConfig(0.5, 3.0, 7),
            "historical-c1-v1",
        )
        state = HistoricalAnalyzerState(
            cusum_state=CusumState(
                positive=2.5,
                negative=0.25,
            ),
            previous_eligible_statistic=2.5,
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "historical_state.json"
            store = FileHistoricalStateStore(path)

            store.save(key, state)

            reopened_store = FileHistoricalStateStore(path)
            restored = reopened_store.load(key)

        self.assertEqual(restored, state)

    def test_unknown_stream_returns_initial_state(self) -> None:
        first_key = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            C1DetectorConfig(0.5, 3.0, 7),
            "historical-c1-v1",
        )
        other_key = HistoricalStreamKey.from_c1(
            "child-002",
            "daily_use_duration_minutes_v1",
            C1DetectorConfig(0.5, 3.0, 7),
            "historical-c1-v1",
        )

        with TemporaryDirectory() as directory:
            store = FileHistoricalStateStore(
                Path(directory) / "historical_state.json"
            )
            store.save(
                first_key,
                HistoricalAnalyzerState(
                    cusum_state=CusumState(positive=4.0),
                    previous_eligible_statistic=4.0,
                ),
            )

            restored = store.load(other_key)

        self.assertEqual(restored, HistoricalAnalyzerState())

    def test_multiple_streams_remain_isolated_after_reopening(self) -> None:
        config = C1DetectorConfig(0.5, 3.0, 7)

        first_key = HistoricalStreamKey.from_c1(
            "child-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )
        second_key = HistoricalStreamKey.from_c1(
            "child-002",
            "daily_use_duration_minutes_v1",
            config,
            "historical-c1-v1",
        )

        first_state = HistoricalAnalyzerState(
            CusumState(positive=1.5),
            1.5,
        )
        second_state = HistoricalAnalyzerState(
            CusumState(negative=2.0),
            2.0,
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "historical_state.json"
            store = FileHistoricalStateStore(path)

            store.save(first_key, first_state)
            store.save(second_key, second_state)

            reopened_store = FileHistoricalStateStore(path)

            self.assertEqual(
                reopened_store.load(first_key),
                first_state,
            )
            self.assertEqual(
                reopened_store.load(second_key),
                second_state,
            )

class HistoricalRepresentationPersistenceTests(unittest.TestCase):
    @staticmethod
    def _representation(
        record_id: str,
        day_offset: int,
        value: float,
    ) -> HistoricalRepresentation:
        start = datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        ) + timedelta(days=day_offset)

        return HistoricalRepresentation(
            representation_record_id=record_id,
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=value,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(
                value=0.95,
                basis="temporal",
            ),
            quality_flags=("delayed_collection",),
            provenance=Provenance(
                source_id="android-usage-events",
                source_version="1",
                source_semantics="daily_total_use",
                adapter_version="v1",
                input_fingerprint="fingerprint-001",
            ),
            computed_at=start + timedelta(
                days=1,
                minutes=5,
            ),
        )

    def test_representation_round_trip_preserves_semantics(self) -> None:
        representation = self._representation(
            "record-001",
            0,
            120.5,
        )

        payload = serialize_historical_representation(
            representation
        )
        restored = deserialize_historical_representation(
            payload
        )

        self.assertEqual(restored, representation)

    def test_duplicate_record_id_is_idempotent(self) -> None:
        representation = self._representation(
            "record-001",
            0,
            120.5,
        )

        with TemporaryDirectory() as directory:
            store = FileHistoricalRepresentationStore(
                Path(directory) / "historical_representations.json"
            )

            first_added = store.append(representation)
            second_added = store.append(representation)

            history = store.load_history(
                subject_id="child-001",
                representation_spec_id="daily_use_duration_minutes_v1",
            )

        self.assertTrue(first_added)
        self.assertFalse(second_added)
        self.assertEqual(history, [representation])

    def test_history_is_loaded_in_behavioral_interval_order(self) -> None:
        later = self._representation(
            "record-002",
            1,
            140.0,
        )
        earlier = self._representation(
            "record-001",
            0,
            120.0,
        )

        with TemporaryDirectory() as directory:
            store = FileHistoricalRepresentationStore(
                Path(directory) / "historical_representations.json"
            )

            store.append(later)
            store.append(earlier)

            history = store.load_history(
                subject_id="child-001",
                representation_spec_id="daily_use_duration_minutes_v1",
            )

        self.assertEqual(
            [item.representation_record_id for item in history],
            ["record-001", "record-002"],
        )

    def test_same_record_id_with_different_content_is_rejected(self) -> None:
        original = self._representation(
            "record-001",
            0,
            120.0,
        )
        conflicting = self._representation(
            "record-001",
            0,
            180.0,
        )

        with TemporaryDirectory() as directory:
            store = FileHistoricalRepresentationStore(
                Path(directory) / "historical_representations.json"
            )

            store.append(original)

            with self.assertRaisesRegex(
                ValueError,
                "contenido diferente",
            ):
                store.append(conflicting)

            history = store.load_history(
                subject_id="child-001",
                representation_spec_id="daily_use_duration_minutes_v1",
            )

        self.assertEqual(history, [original])

class HistoricalRestartContinuityTests(unittest.TestCase):
    @staticmethod
    def _representation(
        day: int,
        value: float,
    ) -> HistoricalRepresentation:
        start = datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        ) + timedelta(days=day)

        return HistoricalRepresentation(
            representation_record_id=f"restart-rep-{day}",
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-restart-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=value,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(),
            provenance=Provenance(
                source_id="restart-continuity-test"
            ),
            computed_at=start + timedelta(days=1),
        )

    @staticmethod
    def _analyze(
        current: HistoricalRepresentation,
        history: list[HistoricalRepresentation],
        state: HistoricalAnalyzerState,
        config: C1DetectorConfig,
        suffix: str,
    ):
        timestamp = current.interval_end + timedelta(minutes=1)

        return analyze_c1_representation(
            current=current,
            history=history,
            previous_state=state,
            config=config,
            evaluation_id=f"restart-eval-{suffix}",
            event_id=f"restart-event-{suffix}",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=timestamp,
            emitted_at=timestamp,
        )

    def test_restart_produces_same_next_analysis_as_continuous_execution(
        self,
    ) -> None:
        config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )

        representations = [
            self._representation(0, 90.0),
            self._representation(1, 100.0),
            self._representation(2, 110.0),
            self._representation(3, 130.0),
            self._representation(4, 160.0),
        ]

        initial_history = representations[:3]
        first_current = representations[3]
        second_current = representations[4]

        first_result = self._analyze(
            current=first_current,
            history=initial_history,
            state=HistoricalAnalyzerState(),
            config=config,
            suffix="first",
        )

        continuous_result = self._analyze(
            current=second_current,
            history=initial_history + [first_current],
            state=first_result.next_state,
            config=config,
            suffix="second",
        )

        stream_key = HistoricalStreamKey.from_c1(
            subject_id="child-restart-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            config=config,
            analysis_version="historical_analyzer_v1",
        )

        with TemporaryDirectory() as directory:
            directory_path = Path(directory)

            history_path = (
                directory_path
                / "historical_representations.json"
            )
            state_path = (
                directory_path
                / "historical_state.json"
            )

            history_store = FileHistoricalRepresentationStore(
                history_path
            )
            state_store = FileHistoricalStateStore(
                state_path
            )

            for representation in (
                initial_history + [first_current]
            ):
                history_store.append(representation)

            state_store.save(
                stream_key,
                first_result.next_state,
            )

            reopened_history_store = (
                FileHistoricalRepresentationStore(
                    history_path
                )
            )
            reopened_state_store = FileHistoricalStateStore(
                state_path
            )

            restored_history = (
                reopened_history_store.load_history(
                    subject_id="child-restart-001",
                    representation_spec_id=(
                        "daily_use_duration_minutes_v1"
                    ),
                )
            )
            restored_state = reopened_state_store.load(
                stream_key
            )

            restarted_result = self._analyze(
                current=second_current,
                history=restored_history,
                state=restored_state,
                config=config,
                suffix="second",
            )

        self.assertEqual(
            restored_history,
            initial_history + [first_current],
        )
        self.assertEqual(
            restored_state,
            first_result.next_state,
        )
        self.assertEqual(
            restarted_result.reference,
            continuous_result.reference,
        )
        self.assertEqual(
            restarted_result.evaluation,
            continuous_result.evaluation,
        )
        self.assertEqual(
            restarted_result.emission,
            continuous_result.emission,
        )
        self.assertEqual(
            restarted_result.next_state,
            continuous_result.next_state,
        )

class HistoricalRepositoryTests(unittest.TestCase):
    def test_representation_and_state_survive_same_repository_update(
        self,
    ) -> None:
        start = datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        )

        representation = HistoricalRepresentation(
            representation_record_id="atomic-rep-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-atomic-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=120.0,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(),
            provenance=Provenance(
                source_id="atomic-persistence-test"
            ),
            computed_at=start + timedelta(days=1),
        )

        config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )
        key = HistoricalStreamKey.from_c1(
            subject_id="child-atomic-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            config=config,
            analysis_version="historical_analyzer_v1",
        )
        state = HistoricalAnalyzerState(
            cusum_state=CusumState(
                positive=2.5,
                negative=0.25,
            ),
            previous_eligible_statistic=2.5,
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "historical_store.json"
            repository = FileHistoricalRepository(path)

            added = repository.save_analysis_progress(
                representation=representation,
                stream_key=key,
                state=state,
            )

            reopened = FileHistoricalRepository(path)

            history = reopened.load_history(
                subject_id="child-atomic-001",
                representation_spec_id="daily_use_duration_minutes_v1",
            )
            restored_state = reopened.load_state(key)

        self.assertTrue(added)
        self.assertEqual(history, [representation])
        self.assertEqual(restored_state, state)

    def test_duplicate_progress_update_is_idempotent(self) -> None:
        start = datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        )

        representation = HistoricalRepresentation(
            representation_record_id="atomic-rep-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-atomic-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=120.0,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(),
            provenance=Provenance(
                source_id="atomic-persistence-test"
            ),
            computed_at=start + timedelta(days=1),
        )

        config = C1DetectorConfig(0.5, 3.0, 3)
        key = HistoricalStreamKey.from_c1(
            "child-atomic-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical_analyzer_v1",
        )
        state = HistoricalAnalyzerState(
            CusumState(positive=2.5),
            2.5,
        )

        with TemporaryDirectory() as directory:
            repository = FileHistoricalRepository(
                Path(directory) / "historical_store.json"
            )

            first = repository.save_analysis_progress(
                representation=representation,
                stream_key=key,
                state=state,
            )
            second = repository.save_analysis_progress(
                representation=representation,
                stream_key=key,
                state=state,
            )

            history = repository.load_history(
                subject_id="child-atomic-001",
                representation_spec_id="daily_use_duration_minutes_v1",
            )

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(history, [representation])

    def test_failure_before_replace_preserves_previous_repository_version(
        self,
    ) -> None:
        start = datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        )

        first = HistoricalRepresentation(
            representation_record_id="atomic-rep-001",
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-atomic-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start,
            interval_end=start + timedelta(days=1),
            value=120.0,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(),
            provenance=Provenance(
                source_id="atomic-persistence-test"
            ),
            computed_at=start + timedelta(days=1),
        )

        second = HistoricalRepresentation(
            representation_record_id="atomic-rep-002",
            representation_spec_id="daily_use_duration_minutes_v1",
            subject_id="child-atomic-001",
            phenomenon="DAILY_USE_DURATION",
            interval_start=start + timedelta(days=1),
            interval_end=start + timedelta(days=2),
            value=180.0,
            unit="minutes",
            status=ObservationStatus.OBSERVED,
            coverage=Coverage(),
            provenance=Provenance(
                source_id="atomic-persistence-test"
            ),
            computed_at=start + timedelta(days=2),
        )

        config = C1DetectorConfig(0.5, 3.0, 3)
        key = HistoricalStreamKey.from_c1(
            "child-atomic-001",
            "daily_use_duration_minutes_v1",
            config,
            "historical_analyzer_v1",
        )

        first_state = HistoricalAnalyzerState(
            CusumState(positive=1.0),
            1.0,
        )
        second_state = HistoricalAnalyzerState(
            CusumState(positive=4.0),
            4.0,
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "historical_store.json"
            repository = FileHistoricalRepository(path)

            repository.save_analysis_progress(
                representation=first,
                stream_key=key,
                state=first_state,
            )

            with patch(
                "historical.persistence.os.replace",
                side_effect=OSError("fallo simulado antes del replace"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "fallo simulado",
                ):
                    repository.save_analysis_progress(
                        representation=second,
                        stream_key=key,
                        state=second_state,
                    )

            reopened = FileHistoricalRepository(path)

            history = reopened.load_history(
                subject_id="child-atomic-001",
                representation_spec_id=(
                    "daily_use_duration_minutes_v1"
                ),
            )
            restored_state = reopened.load_state(key)

            temporary_path = path.with_name(
                f".{path.name}.tmp"
            )

            self.assertFalse(temporary_path.exists())

        self.assertEqual(history, [first])
        self.assertEqual(restored_state, first_state)

if __name__ == "__main__":
    unittest.main()
