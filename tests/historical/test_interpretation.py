import unittest
from datetime import datetime, timedelta, timezone

from historical.analyzer import (
    HistoricalAnalyzerState,
    analyze_c1_representation,
)
from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.detector import C1DetectorConfig, CusumState
from historical.interpretation import (
    ChangeDirection,
    HistoricalInterpretation,
    build_historical_interpretation,
)


UTC = timezone.utc
BASE_TIME = datetime(2026, 9, 1, tzinfo=UTC)


def make_representation(
    record_id: str,
    day: int,
    value: float,
) -> HistoricalRepresentation:
    start = BASE_TIME + timedelta(days=day)

    return HistoricalRepresentation(
        representation_record_id=record_id,
        representation_spec_id="daily-use-duration-v1",
        subject_id="child-1",
        phenomenon="DAILY_USE_DURATION",
        interval_start=start,
        interval_end=start + timedelta(days=1),
        value=value,
        unit="minutes",
        status=(
            ObservationStatus.OBSERVED_ZERO
            if value == 0
            else ObservationStatus.OBSERVED
        ),
        coverage=Coverage(
            value=1.0,
            basis="query_interval",
        ),
        quality_flags=(),
        provenance=Provenance(
            source_id="test",
        ),
        computed_at=start + timedelta(days=1),
    )


class HistoricalInterpretationTests(unittest.TestCase):
    def build_emitting_scenario(
        self,
        *,
        current_value: float = 160.0,
        previous_state: HistoricalAnalyzerState | None = None,
    ):
        history_values = [90.0, 100.0, 110.0]

        history = [
            make_representation(
                f"history-{index}",
                index,
                value,
            )
            for index, value in enumerate(history_values)
        ]

        current = make_representation(
            "current",
            3,
            current_value,
        )

        config = C1DetectorConfig(
            k=0.5,
            threshold=3.0,
            min_history=3,
        )

        result = analyze_c1_representation(
            current=current,
            history=history,
            previous_state=(
                previous_state
                if previous_state is not None
                else HistoricalAnalyzerState(
                    cusum_state=CusumState(),
                    previous_eligible_statistic=0.0,
                )
            ),
            config=config,
            evaluation_id="evaluation-1",
            event_id="event-1",
            analysis_version="test-analysis-v1",
            emitter_version="test-emitter-v1",
            computed_at=current.interval_end,
            emitted_at=current.interval_end,
        )

        return current, result

    def test_emitted_event_builds_descriptive_interpretation(self):
        current, result = self.build_emitting_scenario()

        interpretation = build_historical_interpretation(
            current=current,
            result=result,
            interpretation_id="interpretation-1",
            interpretation_version="interpretation-v1",
            computed_at=current.interval_end,
        )

        self.assertEqual(
            interpretation.detection_event_id,
            "event-1",
        )
        self.assertEqual(
            interpretation.phenomenon,
            "DAILY_USE_DURATION",
        )
        self.assertEqual(
            interpretation.unit,
            "minutes",
        )
        self.assertEqual(
            interpretation.observed_value,
            160.0,
        )
        self.assertEqual(
            interpretation.reference_value,
            100.0,
        )
        self.assertEqual(
            interpretation.value_change,
            60.0,
        )
        self.assertAlmostEqual(
            interpretation.relative_change,
            0.6,
        )
        self.assertEqual(
            interpretation.direction,
            ChangeDirection.INCREASE,
        )

    def test_negative_change_is_described_as_decrease(self):
        current, result = self.build_emitting_scenario(
            current_value=40.0,
        )

        interpretation = build_historical_interpretation(
            current=current,
            result=result,
            interpretation_id="interpretation-1",
            interpretation_version="interpretation-v1",
            computed_at=current.interval_end,
        )

        self.assertEqual(
            interpretation.reference_value,
            100.0,
        )
        self.assertEqual(
            interpretation.value_change,
            -60.0,
        )
        self.assertAlmostEqual(
            interpretation.relative_change,
            -0.6,
        )
        self.assertEqual(
            interpretation.direction,
            ChangeDirection.DECREASE,
        )

    def test_interpretation_preserves_quality_context(self):
        current, result = self.build_emitting_scenario()

        interpretation = build_historical_interpretation(
            current=current,
            result=result,
            interpretation_id="interpretation-1",
            interpretation_version="interpretation-v1",
            computed_at=current.interval_end,
        )

        self.assertEqual(
            interpretation.coverage,
            current.coverage,
        )
        self.assertEqual(
            interpretation.quality_flags,
            current.quality_flags,
        )
        self.assertEqual(
            interpretation.reference_history_count,
            result.evaluation.reference_history_count,
        )
        self.assertEqual(
            interpretation.reference_cutoff,
            result.evaluation.reference_cutoff,
        )

    def test_no_emission_cannot_be_interpreted(self):
        history = [
            make_representation("history-0", 0, 90.0),
            make_representation("history-1", 1, 100.0),
            make_representation("history-2", 2, 110.0),
        ]
        current = make_representation(
            "current",
            3,
            100.0,
        )

        result = analyze_c1_representation(
            current=current,
            history=history,
            previous_state=HistoricalAnalyzerState(
                previous_eligible_statistic=0.0,
            ),
            config=C1DetectorConfig(
                k=0.5,
                threshold=3.0,
                min_history=3,
            ),
            evaluation_id="evaluation-1",
            event_id="event-1",
            analysis_version="test-analysis-v1",
            emitter_version="test-emitter-v1",
            computed_at=current.interval_end,
            emitted_at=current.interval_end,
        )

        with self.assertRaises(ValueError):
            build_historical_interpretation(
                current=current,
                result=result,
                interpretation_id="interpretation-1",
                interpretation_version="interpretation-v1",
                computed_at=current.interval_end,
            )

    def test_naive_computed_at_is_rejected(self):
        current, result = self.build_emitting_scenario()

        with self.assertRaises(ValueError):
            build_historical_interpretation(
                current=current,
                result=result,
                interpretation_id="interpretation-1",
                interpretation_version="interpretation-v1",
                computed_at=datetime(2026, 9, 5),
            )

    def test_different_representation_cannot_reuse_event(self):
        current, result = self.build_emitting_scenario()

        other = make_representation(
            "other-current",
            4,
            170.0,
        )

        with self.assertRaises(ValueError):
            build_historical_interpretation(
                current=other,
                result=result,
                interpretation_id="interpretation-1",
                interpretation_version="interpretation-v1",
                computed_at=other.interval_end,
            )

    def test_blank_interpretation_identity_is_rejected(self):
        current, result = self.build_emitting_scenario()

        with self.assertRaises(ValueError):
            build_historical_interpretation(
                current=current,
                result=result,
                interpretation_id=" ",
                interpretation_version="interpretation-v1",
                computed_at=current.interval_end,
            )

    def test_blank_interpretation_version_is_rejected(self):
        current, result = self.build_emitting_scenario()

        with self.assertRaises(ValueError):
            build_historical_interpretation(
                current=current,
                result=result,
                interpretation_id="interpretation-1",
                interpretation_version=" ",
                computed_at=current.interval_end,
            )

    def test_interpretation_contract_excludes_decision_and_clinical_semantics(
        self,
    ) -> None:
        excluded_fields = {
            "risk",
            "risk_level",
            "severity",
            "clinical_meaning",
            "problematic_use",
            "improvement",
            "worsening",
            "persistence_days",
            "change_started_at",
            "communicable",
            "alert",
            "recommendation",
        }

        self.assertTrue(
            excluded_fields.isdisjoint(
                HistoricalInterpretation.__dataclass_fields__
            )
        )

if __name__ == "__main__":
    unittest.main()