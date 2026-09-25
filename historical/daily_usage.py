"""Contratos mínimos para reconstruir duración diaria de pantalla interactiva."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .contracts import (
    BehavioralObservation,
    Coverage,
    ObservationStatus,
    Provenance,
)

class ScreenStateEventType(str, Enum):
    """Estados de pantalla necesarios para reconstruir intervalos observables."""

    INTERACTIVE = "INTERACTIVE"
    NON_INTERACTIVE = "NON_INTERACTIVE"


@dataclass(frozen=True)
class ScreenStateEvent:
    """Evento normalizado de cambio del estado interactivo de la pantalla."""

    occurred_at: datetime
    event_type: ScreenStateEventType

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError(
                "occurred_at debe incluir información de zona horaria."
            )

@dataclass(frozen=True)
class DailyInteractiveDuration:
    """Resultado técnico de reconstruir intervalos de pantalla interactiva."""

    duration_minutes: float
    has_open_interval: bool

    def __post_init__(self) -> None:
        duration = float(self.duration_minutes)

        if not math.isfinite(duration) or duration < 0.0:
            raise ValueError(
                "duration_minutes debe ser finito y no negativo."
            )


def calculate_interactive_duration(
    events: list[ScreenStateEvent],
) -> DailyInteractiveDuration:
    """Suma únicamente intervalos interactivos que tienen cierre observable."""

    ordered_events = sorted(events, key=lambda event: event.occurred_at)

    interactive_since: datetime | None = None
    accumulated_seconds = 0.0

    for event in ordered_events:
        if event.event_type is ScreenStateEventType.INTERACTIVE:
            if interactive_since is None:
                interactive_since = event.occurred_at
            continue

        if (
            event.event_type is ScreenStateEventType.NON_INTERACTIVE
            and interactive_since is not None
        ):
            accumulated_seconds += (
                event.occurred_at - interactive_since
            ).total_seconds()
            interactive_since = None

    return DailyInteractiveDuration(
        duration_minutes=accumulated_seconds / 60.0,
        has_open_interval=interactive_since is not None,
    )

def build_daily_use_observation(
    *,
    observation_id: str,
    subject_id: str,
    interval_start: datetime,
    interval_end: datetime,
    computed_at: datetime,
    reconstruction: DailyInteractiveDuration,
    capture_complete: bool,
    provenance: Provenance,
) -> BehavioralObservation:
    """Construye la observación diaria sin convertir captura incompleta en uso válido."""

    is_complete = capture_complete and not reconstruction.has_open_interval

    if not is_complete:
        return BehavioralObservation(
            observation_id=observation_id,
            subject_id=subject_id,
            interval_start=interval_start,
            interval_end=interval_end,
            phenomenon="DAILY_USE_DURATION",
            value=None,
            unit="minutes",
            status=ObservationStatus.MISSING,
            coverage=Coverage(
                value=None,
                basis="daily_capture_completeness_not_quantified",
            ),
            quality_flags=("INCOMPLETE_DAILY_CAPTURE",),
            provenance=provenance,
            computed_at=computed_at,
        )

    status = (
        ObservationStatus.OBSERVED_ZERO
        if reconstruction.duration_minutes == 0.0
        else ObservationStatus.OBSERVED
    )

    return BehavioralObservation(
        observation_id=observation_id,
        subject_id=subject_id,
        interval_start=interval_start,
        interval_end=interval_end,
        phenomenon="DAILY_USE_DURATION",
        value=reconstruction.duration_minutes,
        unit="minutes",
        status=status,
        coverage=Coverage(
            value=None,
            basis="daily_capture_completeness_not_quantified",
        ),
        provenance=provenance,
        computed_at=computed_at,
    )