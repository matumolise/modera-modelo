"""Adaptador offline del par JSON/JSONL emitido por DiagnosticExport.kt.

No verifica atribución personal ni exhaustividad física de UsageEvents.
Los bytes de entrada forman parte de la procedencia, incluso sus metadatos.
"""

from hashlib import sha256
from collections import Counter
from bisect import bisect_left
from uuid import UUID

from .f12_bridge import BRIDGE_VERSION, build_f12_request, canonical_hash
from .historical_api import parse_historical_request
from .historical_config import identifier
from .json_codec import strict_json

EXPORT_ADAPTER_VERSION = "f12-android-export-adapter-v1-candidate"
MAX_BYTES = 32 * 1024 * 1024
MAX_OVERLAP_COMPARISONS = 100000  # Presupuesto de trabajo, no parámetro de C1.
SUMMARY_FIELDS = {
    "collectorRunId": "collector_run_id", "requestedBeginEpochMs": "requested_begin_epoch_ms",
    "requestedEndEpochMs": "requested_end_epoch_ms", "collectedAtEpochMs": "collected_at_epoch_ms",
    "usageAccessAvailable": "usage_access_available", "queryReturnedNull": "query_returned_null",
    "eventCount": "event_count", "errorCode": "error_code", "errorMessage": "error_message",
}
EVENT_FIELDS = {
    "schemaVersion": "schema_version", "collectorRunId": "collector_run_id",
    "queryBeginEpochMs": "query_begin_epoch_ms", "queryEndEpochMs": "query_end_epoch_ms",
    "collectedAtEpochMs": "collected_at_epoch_ms", "eventTimeEpochMs": "event_time_epoch_ms",
    "eventTypeCode": "event_type_code", "eventTypeName": "event_type_name", "queryOrdinal": "query_ordinal",
}
EXTRA_FIELDS = {"packageName", "className", "androidApiLevel", "manufacturer", "model"}
BINDING_FIELDS = {"schema_version", "request_id", "series", "local_date", "computed_at"}
EVENT_NAMES = {0: "NONE", 1: "ACTIVITY_RESUMED", 2: "ACTIVITY_PAUSED", 5: "CONFIGURATION_CHANGE",
               7: "USER_INTERACTION", 8: "SHORTCUT_INVOCATION", 11: "STANDBY_BUCKET_CHANGED",
               15: "SCREEN_INTERACTIVE", 16: "SCREEN_NON_INTERACTIVE", 17: "KEYGUARD_SHOWN",
               18: "KEYGUARD_HIDDEN", 19: "FOREGROUND_SERVICE_START", 20: "FOREGROUND_SERVICE_STOP",
               23: "ACTIVITY_STOPPED", 26: "DEVICE_SHUTDOWN", 27: "DEVICE_STARTUP"}


def event_name(code, api):
    """Espejo del mapper Kotlin publicado, incluyendo el fallback desconocido."""
    if api < 29:
        if code in {19, 20, 23, 26, 27}:
            return "EVENT_TYPE_" + str(code)
        if code in {1, 2}:
            return {1: "MOVE_TO_FOREGROUND", 2: "MOVE_TO_BACKGROUND"}[code]
    return EVENT_NAMES.get(code, "EVENT_TYPE_" + str(code))


def _object(data, fields):
    value = strict_json(data)
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("Campos de export incompatibles con DiagnosticExport.kt")
    return value


def _int(value):
    # El productor usa Long/Int, nunca booleanos ni números fraccionarios.
    if type(value) is not int or not -(2**63) <= value < 2**63:
        raise ValueError("Entero Android invalido")
    return value


def parse_export_pair(summary_bytes, events_bytes):
    """Valida una consulta íntegra. No ordena ni elimina filas del export."""
    if not isinstance(summary_bytes, bytes) or not isinstance(events_bytes, bytes):
        raise ValueError("Se requieren bytes originales")
    if len(summary_bytes) + len(events_bytes) > MAX_BYTES:
        raise ValueError("Export excesivo")
    summary = _object(summary_bytes, SUMMARY_FIELDS)
    run_id = identifier(summary["collectorRunId"])
    parsed_id = UUID(run_id)
    if str(parsed_id) != run_id or parsed_id.version != 4:
        raise ValueError("collectorRunId no corresponde al UUID v4 del collector")
    for field in ("requestedBeginEpochMs", "requestedEndEpochMs", "collectedAtEpochMs", "eventCount"):
        _int(summary[field])
    begin, end = summary["requestedBeginEpochMs"], summary["requestedEndEpochMs"]
    if begin >= end or summary["eventCount"] < 0 or summary["collectedAtEpochMs"] < end:
        raise ValueError("Limites, conteo o reloj de consulta inconsistentes")
    for field in ("usageAccessAvailable", "queryReturnedNull"):
        if type(summary[field]) is not bool:
            raise ValueError("Estado de captura requiere booleano")
    for field in ("errorCode", "errorMessage"):
        if summary[field] is not None and not isinstance(summary[field], str):
            raise ValueError("Error collector incompatible")
    code = summary["errorCode"]
    states = {
        None: (True, False), "USAGE_ACCESS_NOT_GRANTED": (False, False),
        "QUERY_RETURNED_NULL": (True, True), "SECURITY_EXCEPTION": (True, False),
        "QUERY_RUNTIME_EXCEPTION": (True, False),
    }
    if code not in states or states[code] != (summary["usageAccessAvailable"], summary["queryReturnedNull"]):
        raise ValueError("Estado de captura no emitido por el collector revisado")
    if code is None and summary["errorMessage"] is not None:
        raise ValueError("Mensaje de error en consulta exitosa")
    # splitlines acepta el salto final escrito por appendLine; una fila vacía
    # intermedia es una alteración, no un evento que se pueda descartar.
    lines = events_bytes.splitlines()
    if len(lines) > 100000:
        raise ValueError("Demasiados eventos raw")
    rows = [_object(line, set(EVENT_FIELDS) | EXTRA_FIELDS) for line in lines]
    if len(rows) != summary["eventCount"] or len(rows) > 100000 or (code is not None and rows):
        raise ValueError("Conteo de eventos incompatible con resumen/estado")
    ordinals, hardware, previous = set(), set(), None
    for row in rows:
        if row["schemaVersion"] != "raw-usage-event-v1":
            raise ValueError("Version raw desconocida")
        for field in ("queryBeginEpochMs", "queryEndEpochMs", "collectedAtEpochMs",
                      "eventTimeEpochMs", "eventTypeCode", "queryOrdinal", "androidApiLevel"):
            _int(row[field])
        if not 28 <= row["androidApiLevel"] < 2**31 or not 0 <= row["eventTypeCode"] < 2**31:
            raise ValueError("API/tipo incompatible con collector revisado")
        if (row["collectorRunId"] != run_id or row["queryBeginEpochMs"] != begin
                or row["queryEndEpochMs"] != end
                or row["collectedAtEpochMs"] != summary["collectedAtEpochMs"]
                or not begin <= row["eventTimeEpochMs"] < end):
            raise ValueError("Asociacion consulta/evento o timestamp incompatible")
        if row["eventTypeName"] != event_name(row["eventTypeCode"], row["androidApiLevel"]):
            raise ValueError("Nombre/codigo incompatible con mapper Kotlin")
        for field in ("packageName", "className"):
            if row[field] is not None and not isinstance(row[field], str):
                raise ValueError("Metadato nullable incompatible")
        for field in ("manufacturer", "model"):
            if not isinstance(row[field], str):
                raise ValueError("Metadato Build incompatible")
        hardware.add((row["androidApiLevel"], row["manufacturer"], row["model"]))
        ordinal = row["queryOrdinal"]
        order = (row["eventTimeEpochMs"], ordinal)
        if ordinal < 0 or ordinal in ordinals or (previous is not None and order < previous):
            raise ValueError("Orden u ordinal incompatible con exportador")
        ordinals.add(ordinal)
        previous = order
    if ordinals != set(range(len(rows))) or len(hardware) > 1:
        raise ValueError("Enumeracion truncada o metadatos mezclados")
    return summary, rows, hardware


def _validate_overlaps(queries):
    """No elegir silenciosamente una historia entre snapshots contradictorios."""
    if not any(rows for _, rows in queries):
        return
    successful = sorted(((s, rows, [r["eventTimeEpochMs"] for r in rows])
                         for s, rows in queries if s["errorCode"] is None),
                        key=lambda item: (item[0]["requestedBeginEpochMs"], item[0]["collectorRunId"]))
    active, comparisons = [], 0
    def snapshot(rows, times, begin, end):
        keys = ("schemaVersion", "eventTimeEpochMs", "eventTypeCode", "eventTypeName",
                "packageName", "className", "androidApiLevel", "manufacturer", "model")
        return Counter(tuple(row[k] for k in keys)
                       for row in rows[bisect_left(times, begin):bisect_left(times, end)])
    for summary, rows, times in successful:
        begin, end = summary["requestedBeginEpochMs"], summary["requestedEndEpochMs"]
        active = [(s, r, ts) for s, r, ts in active if s["requestedEndEpochMs"] > begin]
        for previous, earlier, earlier_times in active:
            comparisons += 1
            if comparisons > MAX_OVERLAP_COMPARISONS:
                raise ValueError("Lote excede presupuesto de comparacion de solapamientos")
            overlap_end = min(end, previous["requestedEndEpochMs"])
            if snapshot(rows, times, begin, overlap_end) != snapshot(earlier, earlier_times, begin, overlap_end):
                raise ValueError("Consultas exitosas discrepan en los eventos del tramo solapado")
        active.append((summary, rows, times))


def prepare_android_export(binding, pairs):
    """Produce preparación, payload y auditoría; pares = [(summary, JSONL)]."""
    if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
        raise ValueError("Cabecera backend explicita requerida; no es un export Android")
    if not isinstance(pairs, (list, tuple)) or len(pairs) > 10000:
        raise ValueError("Coleccion de pares incompatible")
    if sum(len(s) + len(e) for s, e in pairs) > MAX_BYTES:
        raise ValueError("Coleccion export excesiva")
    summaries, events, lineage, hardware, seen, queries = [], [], [], set(), set(), []
    for summary_bytes, events_bytes in pairs:
        summary, rows, detected = parse_export_pair(summary_bytes, events_bytes)
        run_id = summary["collectorRunId"]
        if run_id in seen:
            raise ValueError("Consulta repetida: seleccionar una copia original por run")
        seen.add(run_id)
        hardware.update(detected)
        queries.append((summary, rows))
        summaries.append({target: summary[source] for source, target in SUMMARY_FIELDS.items()})
        events.extend({target: row[source] for source, target in EVENT_FIELDS.items()} for row in rows)
        lineage.append({"collector_run_id": run_id, "event_count": len(rows),
                        "summary_sha256": sha256(summary_bytes).hexdigest(),
                        "events_sha256": sha256(events_bytes).hexdigest()})
    if len(hardware) > 1:
        raise ValueError("API/manufacturer/model distintos: revisar origen antes de combinar")
    _validate_overlaps(queries)
    preparation = {**binding, "raw_events": events, "summaries": summaries}
    payload = build_f12_request(preparation)
    lineage.sort(key=lambda item: item["collector_run_id"])
    provenance = payload["representation"]["provenance"]
    projection_fingerprint = provenance["input_fingerprint"]
    provenance["input_fingerprint"] = canonical_hash({
        "export_adapter_version": EXPORT_ADAPTER_VERSION,
        "projection_fingerprint": projection_fingerprint, "originals": lineage,
    })
    # No cambia el adaptador matemático v2 ni la identidad de la serie.
    provenance["source_version"] = EXPORT_ADAPTER_VERSION
    parse_historical_request(payload)
    audit = {"audit_schema": "f12-export-lineage-v1", "export_adapter_version": EXPORT_ADAPTER_VERSION,
             "projection_bridge_version": BRIDGE_VERSION,
             "projection_fingerprint": projection_fingerprint, "originals": lineage,
             "export_evidence_state": "PAIRS_AVAILABLE" if pairs else "NO_EXPORT_DECLARED_BY_BACKEND",
             "hardware_metadata_consistent": True, "hardware_metadata_available": bool(hardware),
             "device_identity_verified": False, "physical_capture_verified": False,
             "coverage_quantified": False}
    return {"preparation": preparation, "request": payload, "audit": audit}
