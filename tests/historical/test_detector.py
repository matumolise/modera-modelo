import unittest
from datetime import datetime, timedelta, timezone

from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.detector import (
    C1DetectorConfig,
    C1_DETECTOR_FAMILY,
    CusumState,
    DetectorEvaluationOutcome,
    evaluate_c1,
)
from historical.eligibility import AnalysisEligibilityReason
from historical.reference import ScalarReference


UTC = timezone.utc


def representation(
    value=12.0,
    *,
    status: ObservationStatus = ObservationStatus.OBSERVED,
) -> HistoricalRepresentation:
    start = datetime(2026, 9, 15, tzinfo=UTC)
    return HistoricalRepresentation(
        representation_record_id="rep-current",
        representation_spec_id="total_use.daily_minutes.v1",
        subject_id="child-001",
        phenomenon="TOTAL_USE_MINUTES",
        interval_start=start,
        interval_end=start + timedelta(days=1),
        value=value,
        unit="minutes",
        status=status,
        coverage=Coverage(value=None, basis="temporal"),
        quality_flags=(),
        provenance=Provenance(source_id="test"),
        computed_at=start + timedelta(days=1, hours=1),
    )


def reference(
    *,
    location: float | None = 10.0,
    scale: float | None = 2.0,
    history_count: int = 5,
    cutoff: datetime | None = None,
) -> ScalarReference:
    return ScalarReference(
        location=location,
        scale=scale,
        history_count=history_count,
        reference_end_exclusive=cutoff
        or datetime(2026, 9, 15, tzinfo=UTC),
    )


def config(
    *,
    k: float = 0.5,
    threshold: float = 3.0,
    min_history: int = 3,
) -> C1DetectorConfig:
    return C1DetectorConfig(
        k=k,
        threshold=threshold,
        min_history=min_history,
    )


def evaluate(
    current: HistoricalRepresentation,
    ref: ScalarReference,
    state: CusumState | None = None,
    cfg: C1DetectorConfig | None = None,
):
    return evaluate_c1(
        current,
        ref,
        state or CusumState(),
        cfg or config(),
        evaluation_id="eval-001",
        analysis_version="historical_analyzer_v1",
        computed_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
    )


class C1DetectorConfigTests(unittest.TestCase):
    def test_k_threshold_and_min_history_are_explicit(self) -> None:
        with self.assertRaises(TypeError):
            C1DetectorConfig()  # type: ignore[call-arg]

    def test_invalid_numeric_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C1DetectorConfig(k=-0.1, threshold=3.0, min_history=3)
        with self.assertRaises(ValueError):
            C1DetectorConfig(k=0.5, threshold=0.0, min_history=3)
        with self.assertRaises(ValueError):
            C1DetectorConfig(k=0.5, threshold=3.0, min_history=0)


class C1DetectorEvaluationTests(unittest.TestCase):
    def test_insufficient_history_abstains_without_advancing_state(self) -> None:
        state = CusumState(positive=1.0, negative=2.0)
        result = evaluate(
            representation(12.0),
            reference(history_count=2),
            state=state,
        )

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertEqual(
            result.evaluation.abstention_reason,
            AnalysisEligibilityReason.INSUFFICIENT_HISTORY,
        )
        self.assertEqual(result.next_state, state)

    def test_non_estimable_reference_abstains_without_advancing_state(self) -> None:
        state = CusumState(positive=1.0, negative=2.0)
        result = evaluate(
            representation(12.0),
            reference(scale=0.0),
            state=state,
        )

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertEqual(
            result.evaluation.abstention_reason,
            AnalysisEligibilityReason.NON_ESTIMABLE_REFERENCE,
        )
        self.assertEqual(result.next_state, state)

    def test_missing_abstains_and_does_not_advance_state(self) -> None:
        state = CusumState(positive=1.0, negative=2.0)
        current = representation(None, status=ObservationStatus.MISSING)
        result = evaluate(current, reference(), state=state)

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertEqual(
            result.evaluation.abstention_reason,
            AnalysisEligibilityReason.CURRENT_MISSING,
        )
        self.assertEqual(result.next_state, state)

    def test_abstain_is_not_no_change(self) -> None:
        result = evaluate(
            representation(None, status=ObservationStatus.NOT_APPLICABLE),
            reference(),
        )

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertNotEqual(
            result.evaluation.outcome,
            DetectorEvaluationOutcome.NO_CHANGE,
        )

    def test_positive_shift_updates_upper_cusum(self) -> None:
        # z=(14-10)/2=2; G+=0+2-0.5=1.5, G-=0.
        result = evaluate(
            representation(14.0),
            reference(),
            cfg=config(k=0.5, threshold=5.0),
        )

        self.assertAlmostEqual(result.next_state.positive, 1.5)
        self.assertAlmostEqual(result.next_state.negative, 0.0)
        self.assertAlmostEqual(result.evaluation.detector_statistic, 1.5)

    def test_negative_shift_updates_lower_cusum(self) -> None:
        # z=(6-10)/2=-2; G-=0-(-2)-0.5=1.5, G+=0.
        result = evaluate(
            representation(6.0),
            reference(),
            cfg=config(k=0.5, threshold=5.0),
        )

        self.assertAlmostEqual(result.next_state.positive, 0.0)
        self.assertAlmostEqual(result.next_state.negative, 1.5)
        self.assertAlmostEqual(result.evaluation.detector_statistic, 1.5)

    def test_previous_state_is_accumulated(self) -> None:
        # z=1, so G+=1.25+1-0.5=1.75.
        result = evaluate(
            representation(12.0),
            reference(),
            state=CusumState(positive=1.25, negative=0.0),
            cfg=config(k=0.5, threshold=5.0),
        )

        self.assertAlmostEqual(result.next_state.positive, 1.75)

    def test_below_threshold_is_no_change(self) -> None:
        result = evaluate(
            representation(14.0),
            reference(),
            cfg=config(k=0.5, threshold=2.0),
        )

        self.assertEqual(
            result.evaluation.outcome,
            DetectorEvaluationOutcome.NO_CHANGE,
        )

    def test_at_or_above_threshold_is_change(self) -> None:
        result = evaluate(
            representation(14.0),
            reference(),
            cfg=config(k=0.5, threshold=1.5),
        )

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.CHANGE)

    def test_change_does_not_hide_or_reset_computed_cusum_state(self) -> None:
        result = evaluate(
            representation(14.0),
            reference(),
            cfg=config(k=0.5, threshold=1.0),
        )

        self.assertEqual(result.evaluation.outcome, DetectorEvaluationOutcome.CHANGE)
        self.assertEqual(result.next_state, CusumState(positive=1.5, negative=0.0))

    def test_same_input_state_and_config_is_deterministic(self) -> None:
        current = representation(14.0)
        ref = reference()
        state = CusumState(positive=0.25, negative=0.0)
        cfg = config(k=0.5, threshold=2.0)

        first = evaluate(current, ref, state=state, cfg=cfg)
        second = evaluate(current, ref, state=state, cfg=cfg)

        self.assertEqual(first, second)

    def test_structured_value_is_not_silently_coerced_into_c1(self) -> None:
        current = representation({"games": 0.5, "education": 0.5})

        with self.assertRaises(TypeError):
            evaluate(current, reference())

    def test_future_reference_cutoff_is_rejected(self) -> None:
        current = representation(12.0)
        invalid_cutoff = current.interval_start + timedelta(seconds=1)

        with self.assertRaises(ValueError):
            evaluate(current, reference(cutoff=invalid_cutoff))

    def test_evaluation_preserves_auditable_reference_and_version_fields(self) -> None:
        current = representation(12.0)
        ref = reference()
        result = evaluate(current, ref)
        evaluation = result.evaluation

        self.assertEqual(evaluation.subject_id, current.subject_id)
        self.assertEqual(
            evaluation.representation_spec_id,
            current.representation_spec_id,
        )
        self.assertEqual(evaluation.reference_cutoff, ref.reference_end_exclusive)
        self.assertEqual(evaluation.reference_history_count, ref.history_count)
        self.assertEqual(evaluation.detector_family, C1_DETECTOR_FAMILY)
        self.assertEqual(evaluation.analysis_version, "historical_analyzer_v1")


if __name__ == "__main__":
    unittest.main()
