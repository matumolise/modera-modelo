"""Historical Analyzer package for Moderá."""

from .analyzer import (
    HistoricalAnalysisResult,
    HistoricalAnalyzerState,
    analyze_c1_representation,
)
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
from .emitter import (
    DetectionEvent,
    DetectionEventDecision,
    DetectionEventEmissionResult,
    decide_detection_event,
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
    "DetectionEvent",
    "DetectionEventDecision",
    "DetectionEventEmissionResult",
    "MAD_NORMAL_CONSISTENCY",
    "Coverage",
    "HistoricalRepresentation",
    "HistoricalAnalysisResult",
    "HistoricalAnalyzerState",
    "ObservationStatus",
    "Provenance",
    "ScalarReference",
    "ReferenceInclusionDecision",
    "ReferenceInclusionReason",
    "analyze_c1_representation",
    "build_scalar_reference",
    "decide_analysis_eligibility",
    "decide_detection_event",
    "evaluate_c1",
    "decide_reference_inclusion",
]
