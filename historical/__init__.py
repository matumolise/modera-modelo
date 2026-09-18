"""Historical Analyzer package for Moderá."""

from .contracts import (
    BehavioralObservation,
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from .detector import (
    C1_DETECTOR_FAMILY,
    C1DetectorConfig,
    C1EvaluationResult,
    CusumState,
    DetectorEvaluation,
    DetectorEvaluationOutcome,
    evaluate_c1,
)
from .reference import (
    MAD_NORMAL_CONSISTENCY,
    ScalarReference,
    build_scalar_reference,
)
from .eligibility import (
    AnalysisEligibilityDecision,
    AnalysisEligibilityReason,
    ReferenceInclusionDecision,
    ReferenceInclusionReason,
    decide_analysis_eligibility,
    decide_reference_inclusion,
)

__all__ = [
    "AnalysisEligibilityDecision",
    "AnalysisEligibilityReason",
    "BehavioralObservation",
    "C1_DETECTOR_FAMILY",
    "C1DetectorConfig",
    "C1EvaluationResult",
    "CusumState",
    "DetectorEvaluation",
    "DetectorEvaluationOutcome",
    "MAD_NORMAL_CONSISTENCY",
    "Coverage",
    "HistoricalRepresentation",
    "ObservationStatus",
    "Provenance",
    "ScalarReference",
    "ReferenceInclusionDecision",
    "ReferenceInclusionReason",
    "build_scalar_reference",
    "decide_analysis_eligibility",
    "evaluate_c1",
    "decide_reference_inclusion",
]
