"""Servicio de procesamiento del analizador histórico de Moderá.

Este módulo coordina la recuperación del historial y del estado analítico,
la evaluación de una nueva representación y la persistencia del progreso.
No interpreta cambios ni genera alertas o recomendaciones.
"""

from __future__ import annotations

from datetime import datetime

from .analyzer import (
    HistoricalAnalysisResult,
    analyze_c1_representation,
)
from .contracts import HistoricalRepresentation
from .detector import C1DetectorConfig
from .persistence import (
    FileHistoricalRepository,
    HistoricalStreamKey,
)


def process_c1_representation(
    *,
    repository: FileHistoricalRepository,
    current: HistoricalRepresentation,
    stream_key: HistoricalStreamKey,
    config: C1DetectorConfig,
    evaluation_id: str,
    event_id: str,
    analysis_version: str,
    emitter_version: str,
    computed_at: datetime,
    emitted_at: datetime,
) -> HistoricalAnalysisResult:
    """Procesa y persiste una nueva representación histórica con C1."""

    expected_key = HistoricalStreamKey.from_c1(
        subject_id=current.subject_id,
        representation_spec_id=current.representation_spec_id,
        config=config,
        analysis_version=analysis_version,
    )

    if stream_key != expected_key:
        raise ValueError(
            "El stream histórico no coincide con la representación, "
            "la configuración o la versión de análisis."
        )

    if repository.contains_representation(
        current.representation_record_id
    ):
        raise ValueError(
            "La representación histórica ya fue procesada."
        )

    history = repository.load_history(
        subject_id=current.subject_id,
        representation_spec_id=current.representation_spec_id,
    )

    if history:
        last = history[-1]

        if current.interval_start < last.interval_end:
            raise ValueError(
                "La representación no respeta el orden temporal "
                "del historial."
            )

    previous_state = repository.load_state(stream_key)

    result = analyze_c1_representation(
        current=current,
        history=history,
        previous_state=previous_state,
        config=config,
        evaluation_id=evaluation_id,
        event_id=event_id,
        analysis_version=analysis_version,
        emitter_version=emitter_version,
        computed_at=computed_at,
        emitted_at=emitted_at,
    )

    repository.save_analysis_progress(
        representation=current,
        stream_key=stream_key,
        state=result.next_state,
    )

    return result