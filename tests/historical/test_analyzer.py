import unittest
from datetime import datetime, timedelta, timezone

from historical import (
    C1DetectorConfig,
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.analyzer import (
    HistoricalAnalyzerState,
    analyze_c1_representation,
)


UTC = timezone.utc


def representation(
    day: int,
    value: float,
    *,
    record_id: str | None = None,
) -> HistoricalRepresentation:
    start = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=day)

    return HistoricalRepresentation(
        representation_record_id=record_id or f"rep-{day}",
        representation_spec_id="daily-use-minutes.v1",
        subject_id="child-001",
        phenomenon="DAILY_TOTAL_USE",
        interval_start=start,
        interval_end=start + timedelta(days=1),
        value=value,
        unit="minutes",
        status=ObservationStatus.OBSERVED,
        coverage=Coverage(),
        provenance=Provenance(source_id="f13-integration-test"),
        computed_at=start + timedelta(days=1),
    )


class HistoricalAnalyzerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )

        # median=100, MAD=10 -> scaled MAD=14.826
        self.history = [
            representation(0, 90.0),
            representation(1, 100.0),
            representation(2, 110.0),
        ]

    def test_complete_flow_builds_reference_evaluates_and_emits_crossing(self) -> None:
        current = representation(3, 160.0)

        initial_state = HistoricalAnalyzerState(
            previous_eligible_statistic=2.5,
        )

        result = analyze_c1_representation(
            current=current,
            history=self.history,
            previous_state=initial_state,
            config=self.config,
            evaluation_id="eval-001",
            event_id="event-001",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=datetime(2026, 9, 5, tzinfo=UTC),
            emitted_at=datetime(2026, 9, 5, 0, 1, tzinfo=UTC),
        )

        self.assertTrue(result.reference.estimable)
        self.assertEqual(result.reference.history_count, 3)
        self.assertEqual(result.evaluation.reference_history_count, 3)
        self.assertIsNotNone(result.emission.event)
        self.assertEqual(result.emission.event.evaluation_id, "eval-001")
        self.assertEqual(
            result.next_state.previous_eligible_statistic,
            result.evaluation.detector_statistic,
        )

    def test_first_eligible_evaluation_does_not_invent_previous_crossing(self) -> None:
        current = representation(3, 160.0)

        result = analyze_c1_representation(
            current=current,
            history=self.history,
            previous_state=HistoricalAnalyzerState(),
            config=self.config,
            evaluation_id="eval-002",
            event_id="event-002",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=datetime(2026, 9, 5, tzinfo=UTC),
            emitted_at=datetime(2026, 9, 5, 0, 1, tzinfo=UTC),
        )

        self.assertIsNone(result.emission.event)
        self.assertIsNotNone(result.next_state.previous_eligible_statistic)

    def test_abstain_preserves_emission_history(self) -> None:
        current = representation(3, 120.0)

        # Constant history -> MAD=0 -> non-estimable reference -> ABSTAIN.
        constant_history = [
            representation(0, 100.0),
            representation(1, 100.0),
            representation(2, 100.0),
        ]

        initial_state = HistoricalAnalyzerState(
            previous_eligible_statistic=2.4,
        )

        result = analyze_c1_representation(
            current=current,
            history=constant_history,
            previous_state=initial_state,
            config=self.config,
            evaluation_id="eval-003",
            event_id="event-003",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=datetime(2026, 9, 5, tzinfo=UTC),
            emitted_at=datetime(2026, 9, 5, 0, 1, tzinfo=UTC),
        )

        self.assertIsNone(result.emission.event)
        self.assertEqual(
            result.next_state.previous_eligible_statistic,
            2.4,
        )
        self.assertEqual(
            result.next_state.cusum_state,
            initial_state.cusum_state,
        )

    def test_current_value_does_not_enter_its_own_reference(self) -> None:
        current = representation(3, 10000.0)

        result = analyze_c1_representation(
            current=current,
            history=self.history,
            previous_state=HistoricalAnalyzerState(),
            config=self.config,
            evaluation_id="eval-004",
            event_id="event-004",
            analysis_version="historical_analyzer_v1",
            emitter_version="historical_emitter_v1",
            computed_at=datetime(2026, 9, 5, tzinfo=UTC),
            emitted_at=datetime(2026, 9, 5, 0, 1, tzinfo=UTC),
        )

        self.assertEqual(result.reference.history_count, 3)
        self.assertEqual(result.reference.location, 100.0)

if __name__ == "__main__":
    unittest.main()
