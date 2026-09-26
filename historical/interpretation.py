"""Interpretación descriptiva de cambios detectados por el analizador histórico.

Este módulo transforma un evento técnico de detección en una descripción
conductual del valor observado respecto de su referencia histórica. No evalúa
riesgo, severidad, relevancia clínica, comunicabilidad ni recomendaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math

from .analyzer import HistoricalAnalysisResult
from .contracts import Coverage, HistoricalRepresentation
from .emitter import DetectionEventDecision


class ChangeDirection(str, Enum):
    """Dirección descriptiva del valor observado respecto de su referencia."""

    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class HistoricalInterpretation:
    """Descripción auditable de un cambio técnico detectado."""

    interpretation_id: str
    subject_id: str
    detection_event_id: str
    evaluation_id: str
    representation_record_id: str
    representation_spec_id: str

    phenomenon: str
    unit: str | None

    evaluated_interval_start: datetime
    evaluated_interval_end: datetime

    observed_value: float
    reference_value: float
    value_change: float
    relative_change: float | None
    direction: ChangeDirection

    reference_history_count: int
    reference_cutoff: datetime

    coverage: Coverage
    quality_flags: tuple[str, ...]

    interpretation_version: str
    computed_at: datetime


def build_historical_interpretation(
    *,
    current: HistoricalRepresentation,
    result: HistoricalAnalysisResult,
    interpretation_id: str,
    interpretation_version: str,
    computed_at: datetime,
) -> HistoricalInterpretation:
    """Construye una interpretación solo cuando el análisis emitió un evento."""

    if not interpretation_id.strip():
        raise ValueError("interpretation_id no puede estar vacío.")

    if not interpretation_version.strip():
        raise ValueError("interpretation_version no puede estar vacía.")

    if computed_at.tzinfo is None or computed_at.utcoffset() is None:
        raise ValueError("computed_at debe incluir zona horaria.")

    if result.emission.decision is not DetectionEventDecision.EMIT:
        raise ValueError(
            "No se puede interpretar un análisis que no emitió un DetectionEvent."
        )

    event = result.emission.event

    if event is None:
        raise ValueError("La emisión EMIT debe contener un DetectionEvent.")

    evaluation = result.evaluation

    if event.evaluation_id != evaluation.evaluation_id:
        raise ValueError("El evento y la evaluación no coinciden.")

    if event.subject_id != current.subject_id:
        raise ValueError("El evento y la representación pertenecen a sujetos distintos.")

    if event.representation_record_id != current.representation_record_id:
        raise ValueError("El evento y la representación no corresponden al mismo registro.")

    if event.representation_spec_id != current.representation_spec_id:
        raise ValueError(
            "El evento y la representación usan especificaciones diferentes."
        )

    if evaluation.representation_record_id != current.representation_record_id:
        raise ValueError(
            "La evaluación y la representación no corresponden al mismo registro."
        )

    observed_value = evaluation.observed_value
    reference_value = evaluation.reference_location

    if observed_value is None or not math.isfinite(observed_value):
        raise ValueError("La interpretación requiere un valor observado finito.")

    if reference_value is None or not math.isfinite(reference_value):
        raise ValueError("La interpretación requiere una referencia finita.")

    value_change = observed_value - reference_value

    if value_change > 0.0:
        direction = ChangeDirection.INCREASE
    elif value_change < 0.0:
        direction = ChangeDirection.DECREASE
    else:
        direction = ChangeDirection.UNCHANGED

    relative_change = (
        None
        if reference_value == 0.0
        else value_change / reference_value
    )

    return HistoricalInterpretation(
        interpretation_id=interpretation_id,
        subject_id=current.subject_id,
        detection_event_id=event.event_id,
        evaluation_id=evaluation.evaluation_id,
        representation_record_id=current.representation_record_id,
        representation_spec_id=current.representation_spec_id,
        phenomenon=current.phenomenon,
        unit=current.unit,
        evaluated_interval_start=evaluation.evaluated_interval_start,
        evaluated_interval_end=evaluation.evaluated_interval_end,
        observed_value=observed_value,
        reference_value=reference_value,
        value_change=value_change,
        relative_change=relative_change,
        direction=direction,
        reference_history_count=evaluation.reference_history_count,
        reference_cutoff=evaluation.reference_cutoff,
        coverage=current.coverage,
        quality_flags=current.quality_flags,
        interpretation_version=interpretation_version,
        computed_at=computed_at,
    )