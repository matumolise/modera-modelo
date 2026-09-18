"""Scalar C1 detector evaluation for Moderá's Historical Analyzer.

This module implements only the sequential evidence calculation retained for
C1: standardization against an externally supplied scalar reference followed by
bilateral CUSUM accumulation.

Important boundaries:
- ``k``, ``threshold`` and ``min_history`` are explicit configuration inputs;
  this module defines no product defaults.
- reference-window selection/adaptation is external to this module.
- an evaluation outcome of ``CHANGE`` means the detector statistic is at or
  above the explicitly supplied threshold for this observation. It is not by
  itself a ``DetectionEvent``.
- DetectionEvent emission/crossing, reset, cooldown and rearm policy are not
  implemented here and therefore remain open product decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
from numbers import Real

from .contracts import HistoricalRepresentation
from .eligibility import (
    AnalysisEligibilityReason,
    decide_analysis_eligibility,
)
from .reference import ScalarReference


C1_DETECTOR_FAMILY = "C1_V1"


class DetectorEvaluationOutcome(str, Enum):
    """Per-observation result of detector evaluation."""

    CHANGE = "CHANGE"
    NO_CHANGE = "NO_CHANGE"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class C1DetectorConfig:
    """Explicit C1 configuration without product defaults."""

    k: float
    threshold: float
    min_history: int

    def __post_init__(self) -> None:
        k = float(self.k)
        threshold = float(self.threshold)

        if not math.isfinite(k) or k < 0.0:
            raise ValueError("k must be finite and non-negative")
        if not math.isfinite(threshold) or threshold <= 0.0:
            raise ValueError("threshold must be finite and greater than 0")
        if self.min_history < 1:
            raise ValueError("min_history must be at least 1")


@dataclass(frozen=True)
class CusumState:
    """Bilateral CUSUM state carried only across eligible evaluations."""

    positive: float = 0.0
    negative: float = 0.0

    def __post_init__(self) -> None:
        positive = float(self.positive)
        negative = float(self.negative)

        if not math.isfinite(positive) or positive < 0.0:
            raise ValueError("positive CUSUM state must be finite and non-negative")
        if not math.isfinite(negative) or negative < 0.0:
            raise ValueError("negative CUSUM state must be finite and non-negative")


@dataclass(frozen=True)
class DetectorEvaluation:
    """Auditable per-observation detector evaluation.

    ``CHANGE`` records threshold exceedance at evaluation level. A later,
    separately versioned emitter may decide whether a CHANGE evaluation creates
    a DetectionEvent (for example using an upward-crossing rule). Keeping these
    layers separate avoids silently freezing reset/rearm/emission policy here.
    """

    evaluation_id: str
    subject_id: str
    representation_record_id: str
    representation_spec_id: str
    evaluated_interval_start: datetime
    evaluated_interval_end: datetime
    outcome: DetectorEvaluationOutcome
    abstention_reason: AnalysisEligibilityReason | None
    observed_value: float | None
    reference_location: float | None
    reference_scale: float | None
    reference_history_count: int
    reference_cutoff: datetime
    detector_family: str
    detector_k: float
    threshold: float
    detector_statistic: float | None
    positive_cusum: float | None
    negative_cusum: float | None
    analysis_version: str
    computed_at: datetime

    def __post_init__(self) -> None:
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
        if not self.analysis_version.strip():
            raise ValueError("analysis_version cannot be blank")

        _require_aware("evaluated_interval_start", self.evaluated_interval_start)
        _require_aware("evaluated_interval_end", self.evaluated_interval_end)
        _require_aware("reference_cutoff", self.reference_cutoff)
        _require_aware("computed_at", self.computed_at)

        if self.evaluated_interval_start >= self.evaluated_interval_end:
            raise ValueError(
                "evaluated_interval_start must be before evaluated_interval_end"
            )
        if self.reference_cutoff > self.evaluated_interval_start:
            raise ValueError(
                "reference_cutoff cannot be after evaluated_interval_start"
            )
        if self.reference_history_count < 0:
            raise ValueError("reference_history_count cannot be negative")

        if self.outcome is DetectorEvaluationOutcome.ABSTAIN:
            if self.abstention_reason is None:
                raise ValueError("ABSTAIN requires abstention_reason")
            if self.detector_statistic is not None:
                raise ValueError("ABSTAIN cannot have detector_statistic")
            if self.positive_cusum is not None or self.negative_cusum is not None:
                raise ValueError("ABSTAIN cannot report advanced CUSUM state")
        else:
            if self.abstention_reason is not None:
                raise ValueError("non-ABSTAIN evaluation cannot have abstention_reason")
            if self.detector_statistic is None:
                raise ValueError("evaluated outcome requires detector_statistic")
            if self.positive_cusum is None or self.negative_cusum is None:
                raise ValueError("evaluated outcome requires CUSUM components")


@dataclass(frozen=True)
class C1EvaluationResult:
    """Evaluation plus the state to carry to the next eligible observation."""

    evaluation: DetectorEvaluation
    next_state: CusumState


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _finite_scalar(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("C1 detector requires a scalar real-valued representation")

    result = float(value)
    if not math.isfinite(result):
        raise ValueError("C1 detector requires a finite current value")
    return result


def _observed_value_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def evaluate_c1(
    current: HistoricalRepresentation,
    reference: ScalarReference,
    previous_state: CusumState,
    config: C1DetectorConfig,
    *,
    evaluation_id: str,
    analysis_version: str,
    computed_at: datetime,
) -> C1EvaluationResult:
    """Evaluate one scalar representation with C1 bilateral CUSUM evidence.

    Mathematical update for eligible observations::

        z_t  = (x_t - m_t) / s_t
        G+_t = max(0, G+_(t-1) + z_t - k)
        G-_t = max(0, G-_(t-1) - z_t - k)
        score_t = max(G+_t, G-_t)

    An ineligible current observation returns ``ABSTAIN`` and leaves the CUSUM
    state unchanged. This function never resets state after CHANGE; any reset or
    rearm policy belongs to a later orchestration/emitter layer.
    """

    _require_aware("computed_at", computed_at)

    if reference.reference_end_exclusive > current.interval_start:
        raise ValueError("reference cutoff violates prequential ordering")

    eligibility = decide_analysis_eligibility(
        current,
        reference_history_count=reference.history_count,
        min_history=config.min_history,
        reference_estimable=reference.estimable,
    )

    if not eligibility.eligible:
        evaluation = DetectorEvaluation(
            evaluation_id=evaluation_id,
            subject_id=current.subject_id,
            representation_record_id=current.representation_record_id,
            representation_spec_id=current.representation_spec_id,
            evaluated_interval_start=current.interval_start,
            evaluated_interval_end=current.interval_end,
            outcome=DetectorEvaluationOutcome.ABSTAIN,
            abstention_reason=eligibility.reason,
            observed_value=_observed_value_or_none(current.value),
            reference_location=reference.location,
            reference_scale=reference.scale,
            reference_history_count=reference.history_count,
            reference_cutoff=reference.reference_end_exclusive,
            detector_family=C1_DETECTOR_FAMILY,
            detector_k=float(config.k),
            threshold=float(config.threshold),
            detector_statistic=None,
            positive_cusum=None,
            negative_cusum=None,
            analysis_version=analysis_version,
            computed_at=computed_at,
        )
        return C1EvaluationResult(evaluation=evaluation, next_state=previous_state)

    current_value = _finite_scalar(current.value)

    # ``reference.estimable`` was checked by eligibility above.
    if reference.location is None or reference.scale is None:
        raise RuntimeError("estimable reference is missing location/scale")

    z_value = (current_value - reference.location) / reference.scale

    positive = max(
        0.0,
        float(previous_state.positive) + z_value - float(config.k),
    )
    negative = max(
        0.0,
        float(previous_state.negative) - z_value - float(config.k),
    )

    next_state = CusumState(positive=positive, negative=negative)
    statistic = max(positive, negative)
    outcome = (
        DetectorEvaluationOutcome.CHANGE
        if statistic >= float(config.threshold)
        else DetectorEvaluationOutcome.NO_CHANGE
    )

    evaluation = DetectorEvaluation(
        evaluation_id=evaluation_id,
        subject_id=current.subject_id,
        representation_record_id=current.representation_record_id,
        representation_spec_id=current.representation_spec_id,
        evaluated_interval_start=current.interval_start,
        evaluated_interval_end=current.interval_end,
        outcome=outcome,
        abstention_reason=None,
        observed_value=current_value,
        reference_location=reference.location,
        reference_scale=reference.scale,
        reference_history_count=reference.history_count,
        reference_cutoff=reference.reference_end_exclusive,
        detector_family=C1_DETECTOR_FAMILY,
        detector_k=float(config.k),
        threshold=float(config.threshold),
        detector_statistic=statistic,
        positive_cusum=positive,
        negative_cusum=negative,
        analysis_version=analysis_version,
        computed_at=computed_at,
    )

    return C1EvaluationResult(evaluation=evaluation, next_state=next_state)
