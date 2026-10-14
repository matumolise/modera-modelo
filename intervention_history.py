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
import os
import tempfile
import threading
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
class InterventionOffer:
    offer_id: str
    child_id: int
    timestamp: str
    source: str
    context: str
    activities_offered: tuple[str, ...]


@dataclass(frozen=True)
class InterventionRecord:
    intervention_id: str
    child_id: int
    timestamp: str
    source: str
    context: str
    activities_offered: tuple[str, ...]
    response: str
    offer_id: str | None
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
    offer_id: str | None = None,
) -> InterventionRecord:
    """
    Crea y valida una interacción observable.
    """

    offered = tuple(
        activities_offered
    )

    if type(child_id) is not int or child_id <= 0:
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

    if offer_id is not None and not offer_id.strip():
        raise ValueError(
            "offer_id no puede estar vacio."
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
        offer_id=offer_id,
        selected_activity_id=selected_activity_id,
    )


# ============================================================
# CREACION DE OFERTA
# ============================================================

def create_intervention_offer(
    child_id: int,
    source: str,
    context: str,
    activities_offered: Iterable[str],
    timestamp: datetime | None = None,
) -> InterventionOffer:
    """
    Crea y valida una oferta observable antes de la respuesta.
    """

    offered = tuple(
        activities_offered
    )

    if type(child_id) is not int or child_id <= 0:
        raise ValueError(
            "child_id debe ser mayor que 0."
        )

    if source not in VALID_SOURCES:
        raise ValueError(
            f"source invalido: {source}"
        )

    if context not in VALID_CONTEXTS:
        raise ValueError(
            f"context invalido: {context}"
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
            "que no existen en el catalogo: "
            f"{sorted(unknown_activity_ids)}"
        )

    event_time = (
        timestamp
        if timestamp is not None
        else datetime.now()
    )

    return InterventionOffer(
        offer_id=str(uuid4()),
        child_id=child_id,
        timestamp=event_time.isoformat(),
        source=source,
        context=context,
        activities_offered=offered,
    )


# ============================================================
# PERSISTENCIA SIMPLE PARA MVP
# ============================================================


_WRITE_LOCK = threading.RLock()


def _append_jsonl(
    payload: dict,
    output_path: str = "data/intervention_history.jsonl",
) -> None:
    """
    Guarda un evento como una linea JSON.
    """

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    from analytics_service.writer_lease import WriterLease
    from intervention_history_reader import read_linked_offer_responses

    payload = dict(payload)
    payload["activities_offered"] = list(payload["activities_offered"])
    kind = payload["event_type"]
    key = "offer_id" if kind == "offer" else "intervention_id"
    encoded = (json.dumps(payload, ensure_ascii=False, allow_nan=False)+"\n").encode("utf-8")
    with _WRITE_LOCK:
        lease = WriterLease(path.with_name(path.name+".writer.lock"))
        temporary = None
        try:
            original = path.read_bytes() if path.exists() else b""
            rows = [json.loads(line) for line in original.decode("utf-8").splitlines()]
            matches = [row for row in rows if row.get("event_type") == kind and row.get(key) == payload[key]]
            if matches:
                if len(matches) != 1 or matches[0] != payload:
                    raise ValueError("Conflicting intervention event identity.")
                read_linked_offer_responses(path)
                return  # Retry of the frozen event: no rewrite, original IDs/times.
            if original and not original.endswith(b"\n"):
                raise ValueError("Incomplete intervention stream; recover before writing.")
            with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(original+encoded)
                stream.flush()
                os.fsync(stream.fileno())
            # Reuse the canonical link validator before replacing any original.
            read_linked_offer_responses(temporary)
            if not lease.valid():
                raise OSError("Intervention writer lease lost.")
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            lease.close()


def append_intervention_offer(
    offer: InterventionOffer,
    output_path: str = "data/intervention_history.jsonl",
) -> None:
    payload = asdict(
        offer
    )
    payload["event_type"] = "offer"
    _append_jsonl(payload, output_path=output_path)


def append_intervention_record(
    record: InterventionRecord,
    output_path: str = "data/intervention_history.jsonl",
) -> None:
    payload = asdict(
        record
    )
    payload["event_type"] = "response"
    _append_jsonl(payload, output_path=output_path)
