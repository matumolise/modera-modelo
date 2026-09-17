import unittest
from datetime import datetime, timedelta, timezone

from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.eligibility import (
    AnalysisEligibilityReason,
    ReferenceInclusionReason,
    decide_analysis_eligibility,
    decide_reference_inclusion,
)


UTC = timezone.utc


def representation(
    *,
    status: ObservationStatus = ObservationStatus.OBSERVED,
    value=120.0,
    record_id: str = "rep-001",
) -> HistoricalRepresentation:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    return HistoricalRepresentation(
        representation_record_id=record_id,
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


class ReferenceInclusionTests(unittest.TestCase):
    def test_history_can_accumulate_before_detector_is_mature(self) -> None:
        current = representation()

        inclusion = decide_reference_inclusion(current)
        eligibility = decide_analysis_eligibility(
            current,
            reference_history_count=0,
            min_history=3,
            reference_estimable=False,
        )

        self.assertTrue(inclusion.included)
        self.assertEqual(inclusion.reason, ReferenceInclusionReason.INCLUDED)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(
            eligibility.reason,
            AnalysisEligibilityReason.INSUFFICIENT_HISTORY,
        )

    def test_observed_zero_can_enter_reference(self) -> None:
        current = representation(
            status=ObservationStatus.OBSERVED_ZERO,
            value=0.0,
        )

        decision = decide_reference_inclusion(current)

        self.assertTrue(decision.included)

    def test_missing_and_not_applicable_never_enter_reference(self) -> None:
        missing = decide_reference_inclusion(
            representation(status=ObservationStatus.MISSING, value=None)
        )
        not_applicable = decide_reference_inclusion(
            representation(status=ObservationStatus.NOT_APPLICABLE, value=None)
        )

        self.assertEqual(missing.reason, ReferenceInclusionReason.MISSING)
        self.assertEqual(
            not_applicable.reason,
            ReferenceInclusionReason.NOT_APPLICABLE,
        )
        self.assertFalse(missing.included)
        self.assertFalse(not_applicable.included)

    def test_non_finite_scalar_never_enters_reference(self) -> None:
        decision = decide_reference_inclusion(
            representation(value=float("inf"))
        )

        self.assertFalse(decision.included)
        self.assertEqual(
            decision.reason,
            ReferenceInclusionReason.NON_FINITE_VALUE,
        )


class AnalysisEligibilityTests(unittest.TestCase):
    def test_non_estimable_reference_abstains(self) -> None:
        decision = decide_analysis_eligibility(
            representation(),
            reference_history_count=5,
            min_history=3,
            reference_estimable=False,
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(
            decision.reason,
            AnalysisEligibilityReason.NON_ESTIMABLE_REFERENCE,
        )

    def test_two_representations_have_independent_eligibility(self) -> None:
        first = decide_analysis_eligibility(
            representation(record_id="rep-a"),
            reference_history_count=2,
            min_history=3,
            reference_estimable=True,
        )
        second = decide_analysis_eligibility(
            representation(record_id="rep-b"),
            reference_history_count=5,
            min_history=3,
            reference_estimable=True,
        )

        self.assertEqual(
            first.reason,
            AnalysisEligibilityReason.INSUFFICIENT_HISTORY,
        )
        self.assertEqual(second.reason, AnalysisEligibilityReason.ELIGIBLE)
        self.assertFalse(first.eligible)
        self.assertTrue(second.eligible)

    def test_missing_current_is_not_eligible_even_with_mature_history(self) -> None:
        decision = decide_analysis_eligibility(
            representation(status=ObservationStatus.MISSING, value=None),
            reference_history_count=10,
            min_history=3,
            reference_estimable=True,
        )

        self.assertEqual(
            decision.reason,
            AnalysisEligibilityReason.CURRENT_MISSING,
        )
        self.assertFalse(decision.eligible)

    def test_min_history_is_explicit_and_not_a_product_default(self) -> None:
        current = representation()

        at_three = decide_analysis_eligibility(
            current,
            reference_history_count=3,
            min_history=3,
            reference_estimable=True,
        )
        below_five = decide_analysis_eligibility(
            current,
            reference_history_count=3,
            min_history=5,
            reference_estimable=True,
        )

        self.assertTrue(at_three.eligible)
        self.assertEqual(
            below_five.reason,
            AnalysisEligibilityReason.INSUFFICIENT_HISTORY,
        )


if __name__ == "__main__":
    unittest.main()
