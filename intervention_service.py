"""
Servicio de intervenciones del MVP.

Conecta:
- decisión del motor;
- actividades ofrecidas;
- respuesta observable del niño;
- persistencia del historial.

No interpreta selección como cumplimiento.
"""

from __future__ import annotations

from datetime import datetime

from intervention_engine import (
    InterventionDecision,
)

from intervention_history import (
    InterventionRecord,
    create_intervention_record,
    append_intervention_record,
)


# ============================================================
# REGISTRAR RESPUESTA A UNA INTERVENCIÓN
# ============================================================

def register_intervention_response(
    child_id: int,
    decision: InterventionDecision,
    response: str,
    selected_activity_id: str | None = None,
    timestamp: datetime | None = None,
    persist: bool = True,
) -> InterventionRecord:
    """
    Registra la respuesta del niño a una intervención
    previamente generada por el motor.
    """

    if not decision.should_intervene:
        raise ValueError(
            "No se puede registrar una respuesta "
            "para una decisión sin intervención."
        )

    if decision.source is None:
        raise ValueError(
            "La intervención no tiene source."
        )

    if decision.context is None:
        raise ValueError(
            "La intervención no tiene context."
        )

    if len(decision.activities) == 0:
        raise ValueError(
            "La intervención no contiene actividades."
        )

    activity_ids = [
        activity.activity_id
        for activity in decision.activities
    ]

    record = create_intervention_record(
        child_id=child_id,
        source=decision.source,
        context=decision.context,
        activities_offered=activity_ids,
        response=response,
        selected_activity_id=selected_activity_id,
        timestamp=timestamp,
    )

    if persist:
        append_intervention_record(
            record
        )

    return record