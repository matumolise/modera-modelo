"""Serialización del resultado técnico conservado para reintentos.

No vuelve a ejecutar el detector ni incorpora interpretación o decisiones
dirigidas a adultos o niños.
"""

from dataclasses import asdict
from datetime import datetime

from .analyzer import (
    HistoricalAnalysisResult,
    HistoricalAnalyzerState,
)
from .detector import CusumState, DetectorEvaluation, DetectorEvaluationOutcome
from .eligibility import AnalysisEligibilityReason
from .emitter import (
    DetectionEvent,
    DetectionEventDecision,
    DetectionEventEmissionResult,
)
from .reference import ScalarReference


EVALUATION_DATES = (
    "evaluated_interval_start", "evaluated_interval_end",
    "reference_cutoff", "computed_at",
)
EVENT_DATES = ("evaluated_interval_start", "evaluated_interval_end", "emitted_at")


def serialize_analysis_result(result: HistoricalAnalysisResult) -> dict:
    """Conserva todos los campos del resultado original en JSON."""
    reference = asdict(result.reference)
    reference["reference_cutoff"] = result.reference.reference_cutoff.isoformat()
    evaluation = asdict(result.evaluation)
    for name in EVALUATION_DATES:
        evaluation[name] = evaluation[name].isoformat()
    evaluation["outcome"] = result.evaluation.outcome.value
    reason = result.evaluation.abstention_reason
    evaluation["abstention_reason"] = None if reason is None else reason.value
    event = None
    if result.emission.event is not None:
        event = asdict(result.emission.event)
        for name in EVENT_DATES:
            event[name] = event[name].isoformat()
    return {
        "reference": reference,
        "evaluation": evaluation,
        "emission": {"decision": result.emission.decision.value, "event": event},
        "next_state": asdict(result.next_state),
    }


def deserialize_analysis_result(payload: dict) -> HistoricalAnalysisResult:
    """Recupera tipos, enums y fechas sin recalcular el resultado."""
    reference = dict(payload["reference"])
    reference["reference_cutoff"] = datetime.fromisoformat(reference["reference_cutoff"])
    evaluation = dict(payload["evaluation"])
    for name in EVALUATION_DATES:
        evaluation[name] = datetime.fromisoformat(evaluation[name])
    evaluation["outcome"] = DetectorEvaluationOutcome(evaluation["outcome"])
    reason = evaluation["abstention_reason"]
    evaluation["abstention_reason"] = (
        None if reason is None else AnalysisEligibilityReason(reason)
    )
    emission = payload["emission"]
    event = None
    if emission["event"] is not None:
        fields = dict(emission["event"])
        for name in EVENT_DATES:
            fields[name] = datetime.fromisoformat(fields[name])
        event = DetectionEvent(**fields)
    state = payload["next_state"]
    return HistoricalAnalysisResult(
        reference=ScalarReference(**reference),
        evaluation=DetectorEvaluation(**evaluation),
        emission=DetectionEventEmissionResult(
            decision=DetectionEventDecision(emission["decision"]), event=event,
        ),
        next_state=HistoricalAnalyzerState(
            cusum_state=CusumState(**state["cusum_state"]),
            previous_eligible_statistic=state["previous_eligible_statistic"],
        ),
    )
