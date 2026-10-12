"""Preflight offline del cierre diario; no scheduler, cola ni política de corrección.

Estados del backend explícitos, ajenos al schema del collector y al endpoint C1.
"""

from datetime import date, timedelta
from importlib import metadata

from .f12_bridge import BRIDGE_VERSION, SERIES_KEYS, _midnight, _zone, canonical_hash
from .historical_config import identifier
from .historical_api import parse_historical_request

PLAN_SCHEMA = "f12-daily-delivery-plan-v1-candidate"


def assess_daily_plan(document):
    """Ordena días declarados de UNA serie, sin inventar los días omitidos."""
    if not isinstance(document, dict) or set(document) != {"plan_schema", "series", "days"}:
        raise ValueError("Plan diario incompatible")
    if document["plan_schema"] != PLAN_SCHEMA:
        raise ValueError("Version de plan incompatible")
    series = document["series"]
    if not isinstance(series, dict) or set(series) != SERIES_KEYS:
        raise ValueError("Serie explicita requerida")
    for field in SERIES_KEYS - {"time_zone"}:
        identifier(series[field])
    zone = _zone(series["time_zone"])
    subject = "series-" + canonical_hash({**series, "bridge_version": BRIDGE_VERSION,
                                        "tzdata_version": metadata.version("tzdata")})
    days = document["days"]
    if not isinstance(days, list) or not 1 <= len(days) <= 10000:
        raise ValueError("Coleccion de dias invalida")
    checked, seen = [], set()
    for item in days:
        if not isinstance(item, dict) or set(item) != {"local_date", "evidence_state", "request"}:
            raise ValueError("Declaracion diaria incompatible")
        day = date.fromisoformat(item["local_date"])
        if day.isoformat() != item["local_date"] or day in seen:
            raise ValueError("Fecha no canonica o duplicada")
        seen.add(day)
        state, request = item["evidence_state"], item["request"]
        if state == "EXPORT_PENDING":
            if request is not None:
                raise ValueError("Export pendiente no admite payload definitivo")
            _midnight(day, zone); _midnight(day + timedelta(days=1), zone)
        elif state in {"EXPORT_READY", "ABSENCE_CONFIRMED"}:
            _, rep = parse_historical_request(request)
            if (rep.subject_id != subject or rep.interval_start != _midnight(day, zone)
                    or rep.interval_end != _midnight(day + timedelta(days=1), zone)
                    or not rep.provenance.input_fingerprint):
                raise ValueError("Payload de otra serie/dia o sin fingerprint")
            if state == "ABSENCE_CONFIRMED" and rep.status.value != "MISSING":
                raise ValueError("Ausencia confirmada requiere MISSING")
        else:
            raise ValueError("Estado de evidencia desconocido")
        checked.append((day, state, request))
    checked.sort(key=lambda row: row[0])
    blocked = None
    result = []
    for day, state, request in checked:
        if state == "EXPORT_PENDING":
            if blocked is None:
                blocked = day.isoformat()
            decision = "WAIT_FOR_EVIDENCE"
        elif blocked is not None:
            decision = "WAIT_FOR_PRECEDING_DAY"
        else:
            decision = "READY_TO_FREEZE"
        result.append({"local_date": day.isoformat(), "decision": decision,
                       "blocking_day": blocked, "payload_fingerprint": canonical_hash(request) if request else None})
    return {"plan_schema": PLAN_SCHEMA, "subject_id": subject, "decisions": result,
            "authorization_verified": False, "payload_persisted": False,
            "http_sent": False, "missing_dates_inferred": False}
