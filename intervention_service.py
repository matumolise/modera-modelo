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
    InterventionOffer,
    InterventionRecord,
    create_intervention_offer,
    create_intervention_record,
    append_intervention_offer,
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


def create_offer_from_decision(
    child_id: int,
    decision: InterventionDecision,
    timestamp: datetime | None = None,
    persist: bool = True,
) -> InterventionOffer:
    if not decision.should_intervene:
        raise ValueError("No se puede ofrecer una decision sin intervencion.")
    if decision.source is None or decision.context is None:
        raise ValueError("La intervencion requiere source y context.")
    if not decision.activities:
        raise ValueError("La intervencion no contiene actividades.")

    offer = create_intervention_offer(
        child_id=child_id,
        source=decision.source,
        context=decision.context,
        activities_offered=[
            activity.activity_id for activity in decision.activities
        ],
        timestamp=timestamp,
    )
    if persist:
        append_intervention_offer(offer)
    return offer


def register_offer_response(
    offer: InterventionOffer,
    response: str,
    selected_activity_id: str | None = None,
    timestamp: datetime | None = None,
    persist: bool = True,
) -> InterventionRecord:
    """Registra una respuesta vinculada con una oferta previa."""
    record = create_intervention_record(
        child_id=offer.child_id,
        source=offer.source,
        context=offer.context,
        activities_offered=offer.activities_offered,
        response=response,
        selected_activity_id=selected_activity_id,
        timestamp=timestamp,
        offer_id=offer.offer_id,
    )
    if persist:
        append_intervention_record(record)
    return record
