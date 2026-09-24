"""Orquestación del analizador histórico de Moderá.

Este módulo conecta la construcción de la referencia histórica, la evaluación
con C1 y la generación del evento técnico cuando corresponde. La interpretación
del cambio, las alertas y las recomendaciones se manejan por separado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from numbers import Real
from typing import Iterable

from .contracts import HistoricalRepresentation
from .detector import (
    C1DetectorConfig,
    CusumState,
    DetectorEvaluation,
    DetectorEvaluationOutcome,
    evaluate_c1,
)
from .emitter import (
    DetectionEventEmissionResult,
    decide_detection_event,
)
from .reference import ScalarReference, build_scalar_reference


@dataclass(frozen=True)
class HistoricalAnalyzerState:
    """Estado necesario para continuar el análisis histórico entre evaluaciones."""

    cusum_state: CusumState = field(default_factory=CusumState)
    previous_eligible_statistic: float | None = None

    def __post_init__(self) -> None:
        if self.previous_eligible_statistic is None:
            return

        value = self.previous_eligible_statistic
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(
                "previous_eligible_statistic debe ser un número real o None"
            )

        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0.0:
            raise ValueError(
                "previous_eligible_statistic debe ser finito y no negativo"
            )


@dataclass(frozen=True)
class HistoricalAnalysisResult:
    """Resultado de una evaluación completa del analizador histórico."""

    reference: ScalarReference
    evaluation: DetectorEvaluation
    emission: DetectionEventEmissionResult
    next_state: HistoricalAnalyzerState


def analyze_c1_representation(
    current: HistoricalRepresentation,
    history: Iterable[HistoricalRepresentation],
    previous_state: HistoricalAnalyzerState,
    config: C1DetectorConfig,
    *,
    evaluation_id: str,
    event_id: str,
    analysis_version: str,
    emitter_version: str,
    computed_at: datetime,
    emitted_at: datetime,
) -> HistoricalAnalysisResult:
    """Ejecuta una evaluación C1 utilizando el historial y el estado previo."""

    reference = build_scalar_reference(
        current=current,
        history=history,
    )

    detector_result = evaluate_c1(
        current=current,
        reference=reference,
        previous_state=previous_state.cusum_state,
        config=config,
        evaluation_id=evaluation_id,
        analysis_version=analysis_version,
        computed_at=computed_at,
    )

    evaluation = detector_result.evaluation

    emission = decide_detection_event(
        evaluation,
        previous_statistic=previous_state.previous_eligible_statistic,
        event_id=event_id,
        emitter_version=emitter_version,
        emitted_at=emitted_at,
    )

    if evaluation.outcome is DetectorEvaluationOutcome.ABSTAIN:
        next_previous_eligible_statistic = (
            previous_state.previous_eligible_statistic
        )
    else:
        next_previous_eligible_statistic = evaluation.detector_statistic

    next_state = HistoricalAnalyzerState(
        cusum_state=detector_result.next_state,
        previous_eligible_statistic=next_previous_eligible_statistic,
    )

    return HistoricalAnalysisResult(
        reference=reference,
        evaluation=evaluation,
        emission=emission,
        next_state=next_state,
    )
