"""Historical Analyzer package for Moderá."""

from .adapters import (
    DAILY_USE_DURATION_ADAPTER_VERSION,
    DAILY_USE_DURATION_PHENOMENON,
    DAILY_USE_DURATION_SPEC_ID,
    adapt_daily_use_duration,
)
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

from .persistence import (
    FileHistoricalRepository,
    HistoricalStreamKey,
)

from .service import process_c1_representation

from .android_usage import (
    AndroidCollectorRunSummary,
    RawAndroidUsageEvent,
    build_daily_use_observation_from_raw_android,
)
from .daily_usage import (
    ScreenStateEvent,
    ScreenStateEventType,
)

__all__ = [
    "AnalysisEligibilityDecision",
    "DAILY_USE_DURATION_ADAPTER_VERSION",
    "DAILY_USE_DURATION_PHENOMENON",
    "DAILY_USE_DURATION_SPEC_ID",
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
    "FileHistoricalRepository",
    "MAD_NORMAL_CONSISTENCY",
    "Coverage",
    "HistoricalRepresentation",
    "HistoricalAnalysisResult",
    "HistoricalAnalyzerState",
    "HistoricalStreamKey",
    "ObservationStatus",
    "Provenance",
    "ScalarReference",
    "ReferenceInclusionDecision",
    "ReferenceInclusionReason",
    "adapt_daily_use_duration",
    "analyze_c1_representation",
    "build_scalar_reference",
    "decide_analysis_eligibility",
    "decide_detection_event",
    "evaluate_c1",
    "decide_reference_inclusion",
    "process_c1_representation",
    "AndroidCollectorRunSummary",
    "RawAndroidUsageEvent",
    "build_daily_use_observation_from_raw_android",
    "DAILY_USE_DURATION_PHENOMENON",
    "ScreenStateEvent",
    "ScreenStateEventType",
]
