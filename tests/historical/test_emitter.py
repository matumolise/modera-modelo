import unittest
from datetime import datetime, timedelta, timezone

from historical.detector import DetectorEvaluation, DetectorEvaluationOutcome
from historical.emitter import (
    DetectionEvent,
    DetectionEventDecision,
    decide_detection_event,
)


UTC = timezone.utc


def evaluation(
    outcome: DetectorEvaluationOutcome,
    *,
    statistic: float | None,
    threshold: float = 3.0,
    positive: float | None = None,
    negative: float | None = None,
) -> DetectorEvaluation:
    start = datetime(2026, 9, 20, tzinfo=UTC)

    if outcome is DetectorEvaluationOutcome.ABSTAIN:
        from historical.eligibility import AnalysisEligibilityReason

        abstention_reason = AnalysisEligibilityReason.CURRENT_MISSING
        statistic = None
        positive = None
        negative = None
        observed_value = None
    else:
        abstention_reason = None
        observed_value = 120.0
        if positive is None:
            positive = statistic
        if negative is None:
            negative = 0.0

    return DetectorEvaluation(
        evaluation_id="eval-current",
        subject_id="child-001",
        representation_record_id="rep-current",
        representation_spec_id="total_use.daily_minutes.v1",
        evaluated_interval_start=start,
        evaluated_interval_end=start + timedelta(days=1),
        outcome=outcome,
        abstention_reason=abstention_reason,
        observed_value=observed_value,
        reference_location=100.0,
        reference_scale=20.0,
        reference_history_count=14,
        reference_cutoff=start,
        detector_family="C1_BILATERAL_CUSUM",
        detector_k=0.5,
        detector_min_history=7,
        threshold=threshold,
        detector_statistic=statistic,
        positive_cusum=positive,
        negative_cusum=negative,
        analysis_version="historical_analyzer_v1",
        computed_at=start + timedelta(days=1, hours=1),
    )


class DetectionEventEmitterTests(unittest.TestCase):
    def test_upward_crossing_emits_event(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.CHANGE,
            statistic=3.2,
            threshold=3.0,
        )

        result = decide_detection_event(
            current,
            previous_statistic=2.8,
            event_id="event-001",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.EMIT)
        self.assertIsInstance(result.event, DetectionEvent)
        self.assertEqual(result.event.evaluation_id, current.evaluation_id)
        self.assertEqual(result.event.subject_id, current.subject_id)
        self.assertEqual(result.event.detector_statistic, 3.2)
        self.assertEqual(result.event.threshold, 3.0)

    def test_remaining_above_threshold_does_not_emit_again(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.CHANGE,
            statistic=4.1,
            threshold=3.0,
        )

        result = decide_detection_event(
            current,
            previous_statistic=3.4,
            event_id="event-002",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.NO_EMIT)
        self.assertIsNone(result.event)

    def test_below_threshold_does_not_emit(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.NO_CHANGE,
            statistic=2.5,
            threshold=3.0,
        )

        result = decide_detection_event(
            current,
            previous_statistic=2.0,
            event_id="event-003",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.NO_EMIT)
        self.assertIsNone(result.event)

    def test_abstain_does_not_emit(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.ABSTAIN,
            statistic=None,
        )

        result = decide_detection_event(
            current,
            previous_statistic=2.8,
            event_id="event-004",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.NO_EMIT)
        self.assertIsNone(result.event)

    def test_exact_threshold_is_an_upward_crossing(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.CHANGE,
            statistic=3.0,
            threshold=3.0,
        )

        result = decide_detection_event(
            current,
            previous_statistic=2.9,
            event_id="event-005",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.EMIT)
        self.assertIsNotNone(result.event)


if __name__ == "__main__":
    unittest.main()

class DetectionEventEmitterBoundaryTests(unittest.TestCase):
    def test_unknown_previous_statistic_does_not_invent_crossing(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.CHANGE,
            statistic=3.5,
            threshold=3.0,
        )

        result = decide_detection_event(
            current,
            previous_statistic=None,
            event_id="event-boundary-001",
            emitter_version="historical_emitter_v1",
            emitted_at=datetime(2026, 9, 21, 2, tzinfo=UTC),
        )

        self.assertEqual(result.decision, DetectionEventDecision.NO_EMIT)
        self.assertIsNone(result.event)

    def test_naive_emitted_at_is_rejected(self) -> None:
        current = evaluation(
            DetectorEvaluationOutcome.CHANGE,
            statistic=3.5,
            threshold=3.0,
        )

        with self.assertRaises(ValueError):
            decide_detection_event(
                current,
                previous_statistic=2.5,
                event_id="event-boundary-002",
                emitter_version="historical_emitter_v1",
                emitted_at=datetime(2026, 9, 21, 2),
            )

    def test_detection_event_rejects_statistic_below_threshold(self) -> None:
        start = datetime(2026, 9, 20, tzinfo=UTC)

        with self.assertRaises(ValueError):
            DetectionEvent(
                event_id="event-boundary-003",
                evaluation_id="eval-current",
                subject_id="child-001",
                representation_record_id="rep-current",
                representation_spec_id="total_use.daily_minutes.v1",
                evaluated_interval_start=start,
                evaluated_interval_end=start + timedelta(days=1),
                detector_family="C1_BILATERAL_CUSUM",
                detector_statistic=2.9,
                threshold=3.0,
                emitter_version="historical_emitter_v1",
                emitted_at=start + timedelta(days=1, hours=1),
            )

    def test_emission_result_rejects_emit_without_event(self) -> None:
        from historical.emitter import DetectionEventEmissionResult

        with self.assertRaises(ValueError):
            DetectionEventEmissionResult(
                decision=DetectionEventDecision.EMIT,
                event=None,
            )
