"""
Motor de intervenciones del MVP.

Decide si corresponde ofrecer una intervención y,
cuando corresponde, obtiene actividades del catálogo.

Triggers implementados en v1:
- solicitud voluntaria del niño;
- transición previa al horario de sueño.

IMPORTANTE:
- el score del modelo NO dispara automáticamente intervenciones;
- no se utilizan cutoffs clínicos de tiempo, aperturas o sesiones;
- el cooldown es un parámetro operativo del MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from recommendations import (
    Activity,
    CONTEXT_VOLUNTARY,
    CONTEXT_BEDTIME,
    recommend_activities,
)

from intervention_history import (
    SOURCE_CHILD_INITIATED,
    SOURCE_SYSTEM_BEDTIME,
)


# ============================================================
# CONFIGURACIÓN OPERATIVA DEL MVP
# ============================================================

BEDTIME_WINDOW_MINUTES = 60
BEDTIME_COOLDOWN_MINUTES = 60


# ============================================================
# RESULTADO DEL MOTOR
# ============================================================

@dataclass(frozen=True)
class InterventionDecision:
    should_intervene: bool
    source: str | None
    context: str | None
    reason: str
    activities: tuple[Activity, ...]


# ============================================================
# UTILIDADES
# ============================================================

def minutes_until_bedtime(
    current_time: datetime,
    bedtime_hour: int,
    bedtime_minute: int,
) -> float:
    """
    Calcula minutos hasta el próximo horario de sueño.

    Si el horario de sueño de hoy ya pasó,
    toma el del día siguiente.
    """

    if not 0 <= bedtime_hour <= 23:
        raise ValueError(
            "bedtime_hour debe estar entre 0 y 23."
        )

    if not 0 <= bedtime_minute <= 59:
        raise ValueError(
            "bedtime_minute debe estar entre 0 y 59."
        )

    bedtime = current_time.replace(
        hour=bedtime_hour,
        minute=bedtime_minute,
        second=0,
        microsecond=0,
    )

    if bedtime < current_time:
        bedtime += timedelta(days=1)

    delta = bedtime - current_time

    return (
        delta.total_seconds()
        / 60.0
    )


def bedtime_cooldown_elapsed(
    current_time: datetime,
    last_bedtime_intervention: datetime | None,
) -> bool:
    """
    Indica si ya pasó el cooldown operativo.
    """

    if last_bedtime_intervention is None:
        return True

    elapsed = (
        current_time
        - last_bedtime_intervention
    )

    return elapsed >= timedelta(
        minutes=BEDTIME_COOLDOWN_MINUTES
    )


# ============================================================
# SOLICITUD VOLUNTARIA
# ============================================================

def request_voluntary_intervention(
    interests: Iterable[str] | None = None,
    recently_shown_ids: Iterable[str] | None = None,
    random_seed: int | None = None,
) -> InterventionDecision:
    """
    El niño solicita voluntariamente actividades.

    Disponible desde el primer día y no requiere
    detectar previamente ningún patrón.
    """

    activities = recommend_activities(
        context=CONTEXT_VOLUNTARY,
        interests=interests,
        recently_shown_ids=recently_shown_ids,
        n=3,
        random_seed=random_seed,
    )

    return InterventionDecision(
        should_intervene=True,
        source=SOURCE_CHILD_INITIATED,
        context=CONTEXT_VOLUNTARY,
        reason="child_requested_activity",
        activities=tuple(activities),
    )


# ============================================================
# INTERVENCIÓN PREVIA AL SUEÑO
# ============================================================

def evaluate_bedtime_intervention(
    current_time: datetime,
    bedtime_hour: int,
    bedtime_minute: int,
    device_in_use: bool,
    last_bedtime_intervention: datetime | None = None,
    interests: Iterable[str] | None = None,
    recently_shown_ids: Iterable[str] | None = None,
    random_seed: int | None = None,
) -> InterventionDecision:
    """
    Evalúa si corresponde una intervención contextual
    durante la transición previa al sueño.
    """

    if not device_in_use:
        return InterventionDecision(
            should_intervene=False,
            source=None,
            context=None,
            reason="device_not_in_use",
            activities=(),
        )

    minutes_remaining = minutes_until_bedtime(
        current_time=current_time,
        bedtime_hour=bedtime_hour,
        bedtime_minute=bedtime_minute,
    )

    if minutes_remaining > BEDTIME_WINDOW_MINUTES:
        return InterventionDecision(
            should_intervene=False,
            source=None,
            context=None,
            reason="outside_bedtime_window",
            activities=(),
        )

    if not bedtime_cooldown_elapsed(
        current_time=current_time,
        last_bedtime_intervention=last_bedtime_intervention,
    ):
        return InterventionDecision(
            should_intervene=False,
            source=None,
            context=None,
            reason="bedtime_cooldown_active",
            activities=(),
        )

    activities = recommend_activities(
        context=CONTEXT_BEDTIME,
        interests=interests,
        recently_shown_ids=recently_shown_ids,
        n=3,
        random_seed=random_seed,
    )

    return InterventionDecision(
        should_intervene=True,
        source=SOURCE_SYSTEM_BEDTIME,
        context=CONTEXT_BEDTIME,
        reason="bedtime_transition",
        activities=tuple(activities),
    )