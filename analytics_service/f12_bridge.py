"""Preparación offline F12 → representación v2; sin escritura ni llamada HTTP.

La vinculación perfil/dispositivo es responsabilidad del backend autenticado.
La API no obtiene atribución de usuario de eventos SCREEN_INTERACTIVE.
"""

from dataclasses import asdict, replace
from datetime import date, datetime, time, timedelta, timezone
import hashlib
from importlib import metadata, resources
import json
from zoneinfo import ZoneInfo

from historical.adapters import adapt_daily_use_duration
from historical.android_usage import (
    AndroidCollectorRunSummary, RawAndroidUsageEvent,
    build_daily_use_observation_from_raw_android,
)
from historical.contracts import ObservationStatus, Provenance
from historical.persistence import serialize_historical_representation

from .historical_api import _date, parse_historical_request
from .historical_config import identifier

BRIDGE_VERSION = "f12-backend-bridge-v1-candidate"
SERIES_KEYS = {"profile_id", "device_id", "assignment_id", "time_zone", "measurement_version"}
RAW_KEYS = set(RawAndroidUsageEvent.__dataclass_fields__)
RUN_KEYS = set(AndroidCollectorRunSummary.__dataclass_fields__)
EVENT_CODES = {15: "SCREEN_INTERACTIVE", 16: "SCREEN_NON_INTERACTIVE",
               26: "DEVICE_SHUTDOWN", 27: "DEVICE_STARTUP"}


def canonical_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _zone(name):
    # Usar una fuente versionada en ambas plataformas, sin cambiar TZPATH global.
    if (not isinstance(name, str) or not 1 <= len(name) <= 128
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or "\\" in name or name.startswith("/")):
        raise ValueError("Zona IANA invalida")
    parts = name.split("/")
    resource = resources.files("tzdata.zoneinfo")
    for part in parts:
        resource = resource.joinpath(part)
    with resource.open("rb") as stream:
        return ZoneInfo.from_file(stream, key=name)


def _midnight(day, zone):
    naive = datetime.combine(day, time.min)
    candidates = set()
    for fold in (0, 1):
        instant = naive.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == naive:
            candidates.add(instant)
    if len(candidates) != 1:
        raise ValueError("Medianoche local inexistente o ambigua: requiere politica explicita")
    return candidates.pop()


def _raw(row):
    if not isinstance(row, dict) or set(row) != RAW_KEYS:
        raise ValueError("Proyeccion raw F12 incompleta o desconocida")
    for field in RAW_KEYS - {"schema_version", "collector_run_id", "event_type_name"}:
        if type(row[field]) is not int:
            raise ValueError("Campo raw requiere entero: " + field)
    identifier(row["collector_run_id"])
    if not isinstance(row["event_type_name"], str) or not row["event_type_name"].strip():
        raise ValueError("Tipo de evento invalido")
    expected = EVENT_CODES.get(row["event_type_code"])
    if ((expected is not None and expected != row["event_type_name"])
            or (row["event_type_name"] in EVENT_CODES.values() and expected != row["event_type_name"])):
        raise ValueError("Codigo y nombre de evento incompatibles")
    return RawAndroidUsageEvent(**row)


def _run(row):
    if not isinstance(row, dict) or set(row) != RUN_KEYS:
        raise ValueError("Resumen collector incompleto o desconocido")
    identifier(row["collector_run_id"])
    for field in ("requested_begin_epoch_ms", "requested_end_epoch_ms", "collected_at_epoch_ms", "event_count"):
        if type(row[field]) is not int:
            raise ValueError("Campo collector requiere entero")
    for field in ("usage_access_available", "query_returned_null"):
        if type(row[field]) is not bool:
            raise ValueError("Campo collector requiere booleano")
    for field in ("error_code", "error_message"):
        if row[field] is not None and (not isinstance(row[field], str) or not row[field].strip()):
            raise ValueError("Error collector invalido")
    return AndroidCollectorRunSummary(**row)


def build_f12_request(document):
    """Construye un payload estable a conservar ANTES de enviar a analytics."""
    if not isinstance(document, dict) or set(document) != {
        "schema_version", "request_id", "series", "local_date", "computed_at", "raw_events", "summaries"
    } or type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Contrato de preparacion incompatible")
    request_id = identifier(document["request_id"])
    series = document["series"]
    if not isinstance(series, dict) or set(series) != SERIES_KEYS:
        raise ValueError("Identidad de serie explicita requerida")
    for field in SERIES_KEYS - {"time_zone"}:
        identifier(series[field])
    zone = _zone(series["time_zone"])
    tz_version = metadata.version("tzdata")
    binding = {**series, "bridge_version": BRIDGE_VERSION, "tzdata_version": tz_version}
    subject_id = "series-" + canonical_hash(binding)
    day = date.fromisoformat(document["local_date"])
    if day.isoformat() != document["local_date"]:
        raise ValueError("Fecha local debe usar YYYY-MM-DD")
    begin, end = _midnight(day, zone), _midnight(day + timedelta(days=1), zone)
    computed = _date(document["computed_at"])
    if begin >= end or computed < end:
        raise ValueError("Solo dias locales cerrados")
    events, runs = document["raw_events"], document["summaries"]
    if (not isinstance(events, list) or not isinstance(runs, list)
            or len(events) > 100000 or len(runs) > 10000):
        raise ValueError("Coleccion F12 invalida o excesiva")
    raw = [_raw(row) for row in events]
    summaries = [_run(row) for row in runs]
    by_run = {run.collector_run_id: run for run in summaries}
    seen_ordinals, screen_states = set(), {}
    for run in summaries:
        if (run.collected_at_epoch_ms < run.requested_end_epoch_ms
                or run.collected_at_epoch_ms > int(computed.timestamp() * 1000)):
            raise ValueError("Reloj o cierre collector inconsistente")
    for event in raw:
        run = by_run.get(event.collector_run_id)
        ordinal = (event.collector_run_id, event.query_ordinal)
        if ordinal in seen_ordinals or run is None or event.collected_at_epoch_ms != run.collected_at_epoch_ms:
            raise ValueError("Asociacion u ordinal collector incompatible")
        seen_ordinals.add(ordinal)
        if event.event_type_name in {"SCREEN_INTERACTIVE", "SCREEN_NON_INTERACTIVE"}:
            preceding = screen_states.setdefault(event.event_time_epoch_ms, event.event_type_name)
            if preceding != event.event_type_name:
                raise ValueError("Estados contradictorios con el mismo timestamp")
    raw.sort(key=lambda e: (e.event_time_epoch_ms, e.collector_run_id, e.query_ordinal))
    summaries.sort(key=lambda run: run.collector_run_id)
    fingerprint = canonical_hash({"binding": binding, "raw_events": [asdict(e) for e in raw],
                                  "summaries": [asdict(s) for s in summaries]})
    record_id = "rep-" + canonical_hash({"subject_id": subject_id,
                                        "begin": begin.isoformat(), "end": end.isoformat(), "spec": "v2"})
    observation = build_daily_use_observation_from_raw_android(
        observation_id="obs-" + record_id[4:], subject_id=subject_id,
        interval_start=begin, interval_end=end, computed_at=computed,
        raw_events=raw, summaries=summaries,
        provenance=Provenance(source_id="android-usage-events", source_version=BRIDGE_VERSION,
                              source_semantics="Interactive screen duration on assigned device; user attribution unverified",
                              input_fingerprint=fingerprint),
    )
    # El núcleo v2 no resuelve continuidad frente a reinicios. No inventarla.
    begin_ms, end_ms = int(begin.timestamp() * 1000), int(end.timestamp() * 1000)
    prior_states = [e.event_time_epoch_ms for e in raw
                    if e.event_type_name in {"SCREEN_INTERACTIVE", "SCREEN_NON_INTERACTIVE"}
                    and e.event_time_epoch_ms < begin_ms]
    evidence_begin = max(prior_states) if prior_states else begin_ms
    if any(e.event_type_name in {"DEVICE_SHUTDOWN", "DEVICE_STARTUP"}
           and evidence_begin <= e.event_time_epoch_ms < end_ms for e in raw):
        observation = replace(observation, value=None, status=ObservationStatus.MISSING,
                              quality_flags=tuple(sorted(set(observation.quality_flags) | {
                                  "DEVICE_LIFECYCLE_REVIEW_REQUIRED"})))
    representation = adapt_daily_use_duration(observation, representation_record_id=record_id)
    payload = {"request_id": request_id, "representation": serialize_historical_representation(representation)}
    parse_historical_request(payload)  # Exactamente el contrato que admite la API.
    return payload
