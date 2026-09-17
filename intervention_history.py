"""
Registro de interacciones del niño con las intervenciones.

Este módulo registra hechos observables.

IMPORTANTE:
- seleccionar una actividad NO implica haberla realizado;
- rechazar una actividad NO explica por qué fue rechazada;
- la respuesta del niño NO se interpreta como diagnóstico.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
from typing import Iterable

from recommendations import (
    ACTIVITY_CATALOG,
    CONTEXT_VOLUNTARY,
    CONTEXT_BEDTIME,
    CONTEXT_GENERAL,
)

from uuid import uuid4


# ============================================================
# RESPUESTAS VÁLIDAS
# ============================================================

RESPONSE_SELECTED = "selected"
RESPONSE_REJECTED = "rejected"
RESPONSE_POSTPONED = "postponed"
RESPONSE_IGNORED = "ignored"

VALID_RESPONSES = {
    RESPONSE_SELECTED,
    RESPONSE_REJECTED,
    RESPONSE_POSTPONED,
    RESPONSE_IGNORED,
}

# ============================================================
# ORÍGENES VÁLIDOS
# ============================================================

SOURCE_CHILD_INITIATED = "child_initiated"
SOURCE_SYSTEM_BEDTIME = "system_bedtime"

VALID_SOURCES = {
    SOURCE_CHILD_INITIATED,
    SOURCE_SYSTEM_BEDTIME,
}

VALID_CONTEXTS = {
    CONTEXT_VOLUNTARY,
    CONTEXT_BEDTIME,
    CONTEXT_GENERAL,
}

VALID_ACTIVITY_IDS = {
    activity.activity_id
    for activity in ACTIVITY_CATALOG
}


# ============================================================
# REGISTRO
# ============================================================

@dataclass(frozen=True)
class InterventionRecord:
    intervention_id: str
    child_id: int
    timestamp: str
    source: str
    context: str
    activities_offered: tuple[str, ...]
    response: str
    selected_activity_id: str | None


# ============================================================
# CREACIÓN DE REGISTRO
# ============================================================

def create_intervention_record(
    child_id: int,
    source: str,
    context: str,
    activities_offered: Iterable[str],
    response: str,
    selected_activity_id: str | None = None,
    timestamp: datetime | None = None,
) -> InterventionRecord:
    """
    Crea y valida una interacción observable.
    """

    offered = tuple(
        activities_offered
    )

    if child_id <= 0:
        raise ValueError(
            "child_id debe ser mayor que 0."
        )

    if source not in VALID_SOURCES:
        raise ValueError(
            f"source inválido: {source}"
        )

    if context not in VALID_CONTEXTS:
        raise ValueError(
            f"context inválido: {context}"
        )

    if len(offered) == 0:
        raise ValueError(
            "Debe existir al menos una actividad ofrecida."
        )

    if len(offered) != len(set(offered)):
        raise ValueError(
            "activities_offered contiene duplicados."
        )

    unknown_activity_ids = (
        set(offered) - VALID_ACTIVITY_IDS
    )

    if unknown_activity_ids:
        raise ValueError(
            "Se intentaron registrar actividades "
            "que no existen en el catálogo: "
            f"{sorted(unknown_activity_ids)}"
        )

    if response not in VALID_RESPONSES:
        raise ValueError(
            f"Respuesta inválida: {response}"
        )

    # Si seleccionó, tiene que indicar exactamente
    # una actividad que realmente fue ofrecida.
    if response == RESPONSE_SELECTED:

        if selected_activity_id is None:
            raise ValueError(
                "Una respuesta selected requiere "
                "selected_activity_id."
            )

        if selected_activity_id not in offered:
            raise ValueError(
                "La actividad seleccionada no formaba "
                "parte de las actividades ofrecidas."
            )

    # Si NO seleccionó, no debería existir
    # una actividad marcada como elegida.
    else:

        if selected_activity_id is not None:
            raise ValueError(
                "Solo una respuesta selected puede "
                "tener selected_activity_id."
            )

    event_time = (
        timestamp
        if timestamp is not None
        else datetime.now()
    )

    return InterventionRecord(
        intervention_id=str(uuid4()),
        child_id=child_id,
        timestamp=event_time.isoformat(),
        source=source,
        context=context,
        activities_offered=offered,
        response=response,
        selected_activity_id=selected_activity_id,
    )

# ============================================================
# PERSISTENCIA SIMPLE PARA MVP
# ============================================================

def append_intervention_record(
    record: InterventionRecord,
    output_path: str = "data/intervention_history.jsonl",
) -> None:
    """
    Guarda un evento como una línea JSON.

    JSONL permite agregar registros sin reescribir
    todo el historial.
    """

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = asdict(
        record
    )

    # tuple -> list para representación JSON natural.
    payload["activities_offered"] = list(
        payload["activities_offered"]
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
        )

        file.write("\n")