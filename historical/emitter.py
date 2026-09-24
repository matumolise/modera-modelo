"""Detection-event emission for Moderá's Historical Analyzer.

This module converts detector-level evidence into a discrete technical event.

Version 1 implements only an upward-threshold-crossing rule. It deliberately
does not define reset, cooldown, rearm, reference adaptation, alerting, or
recommendation policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
from numbers import Real

from .detector import DetectorEvaluation, DetectorEvaluationOutcome


class DetectionEventDecision(str, Enum):
    EMIT = "EMIT"
    NO_EMIT = "NO_EMIT"


@dataclass(frozen=True)
class DetectionEvent:
    """Auditable technical event produced by an upward threshold crossing."""

    event_id: str
    evaluation_id: str
    subject_id: str
    representation_record_id: str
    representation_spec_id: str
    evaluated_interval_start: datetime
    evaluated_interval_end: datetime
    detector_family: str
    detector_statistic: float
    threshold: float
    emitter_version: str
    emitted_at: datetime

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id cannot be blank")
        if not self.evaluation_id.strip():
            raise ValueError("evaluation_id cannot be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id cannot be blank")
        if not self.representation_record_id.strip():
            raise ValueError("representation_record_id cannot be blank")
        if not self.representation_spec_id.strip():
            raise ValueError("representation_spec_id cannot be blank")
        if not self.detector_family.strip():
            raise ValueError("detector_family cannot be blank")
        if not self.emitter_version.strip():
            raise ValueError("emitter_version cannot be blank")

        _require_aware("evaluated_interval_start", self.evaluated_interval_start)
        _require_aware("evaluated_interval_end", self.evaluated_interval_end)
        _require_aware("emitted_at", self.emitted_at)

        if self.evaluated_interval_start >= self.evaluated_interval_end:
            raise ValueError(
                "evaluated_interval_start must be before evaluated_interval_end"
            )

        statistic = _finite_non_negative(
            "detector_statistic",
            self.detector_statistic,
        )
        threshold = _finite_positive("threshold", self.threshold)

        if statistic < threshold:
            raise ValueError(
                "DetectionEvent requires detector_statistic at or above threshold"
            )


@dataclass(frozen=True)
class DetectionEventEmissionResult:
    decision: DetectionEventDecision
    event: DetectionEvent | None

    def __post_init__(self) -> None:
        if self.decision is DetectionEventDecision.EMIT and self.event is None:
            raise ValueError("EMIT requires an event")
        if self.decision is DetectionEventDecision.NO_EMIT and self.event is not None:
            raise ValueError("NO_EMIT cannot contain an event")


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _finite_non_negative(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")

    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")

    return result


def _finite_positive(name: str, value: object) -> float:
    result = _finite_non_negative(name, value)
    if result <= 0.0:
        raise ValueError(f"{name} must be greater than 0")
    return result


def decide_detection_event(
    current: DetectorEvaluation,
    *,
    previous_statistic: float | None,
    event_id: str,
    emitter_version: str,
    emitted_at: datetime,
) -> DetectionEventEmissionResult:
    """Apply the v1 upward-crossing emission rule.

    An event is emitted only when the current eligible evaluation is CHANGE,
    the previous eligible detector statistic was strictly below the current
    threshold, and the current statistic is at or above that threshold.

    ``previous_statistic=None`` does not establish a crossing and therefore
    does not emit. ABSTAIN never emits.

    This function does not mutate detector state and does not implement reset,
    cooldown, rearm, reference adaptation, alerts, or recommendations.
    """

    _require_aware("emitted_at", emitted_at)

    if current.outcome is DetectorEvaluationOutcome.ABSTAIN:
        return DetectionEventEmissionResult(
            decision=DetectionEventDecision.NO_EMIT,
            event=None,
        )

    if current.detector_statistic is None:
        raise ValueError("non-ABSTAIN evaluation requires detector_statistic")

    current_statistic = _finite_non_negative(
        "current.detector_statistic",
        current.detector_statistic,
    )
    threshold = _finite_positive("current.threshold", current.threshold)

    if previous_statistic is None:
        return DetectionEventEmissionResult(
            decision=DetectionEventDecision.NO_EMIT,
            event=None,
        )

    previous = _finite_non_negative("previous_statistic", previous_statistic)

    upward_crossing = (
        current.outcome is DetectorEvaluationOutcome.CHANGE
        and previous < threshold
        and current_statistic >= threshold
    )

    if not upward_crossing:
        return DetectionEventEmissionResult(
            decision=DetectionEventDecision.NO_EMIT,
            event=None,
        )

    event = DetectionEvent(
        event_id=event_id,
        evaluation_id=current.evaluation_id,
        subject_id=current.subject_id,
        representation_record_id=current.representation_record_id,
        representation_spec_id=current.representation_spec_id,
        evaluated_interval_start=current.evaluated_interval_start,
        evaluated_interval_end=current.evaluated_interval_end,
        detector_family=current.detector_family,
        detector_statistic=current_statistic,
        threshold=threshold,
        emitter_version=emitter_version,
        emitted_at=emitted_at,
    )

    return DetectionEventEmissionResult(
        decision=DetectionEventDecision.EMIT,
        event=event,
    )
