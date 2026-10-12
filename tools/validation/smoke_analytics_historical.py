"""Smoke HTTP con datos ficticios y perfil no calibrado; seed/replay tras reinicio.

Usar únicamente un repositorio/volumen de prueba separado. No es calibración.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from uuid import uuid4


def request(base, path, token, payload=None, authenticated=True):
    headers = {}
    if authenticated:
        headers["Authorization"] = "Bearer " + token
    data = None
    if payload is not None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers,
                                 method="POST" if payload is not None else "GET")
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.code, json.loads(response.read().decode("utf-8"))


def representation(day, value, subject):
    start = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=day)
    return {
        "request_id": "smoke-" + subject + "-" + str(day),
        "representation": {
            "representation_record_id": "rep-" + subject + "-" + str(day),
            "representation_spec_id": "daily_use_duration_minutes_v2", "subject_id": subject,
            "phenomenon": "DAILY_USE_DURATION", "interval_start": start.isoformat(),
            "interval_end": (start + timedelta(days=1)).isoformat(),
            "value": value, "unit": "minutes", "status": "OBSERVED",
            "coverage": {"value": None, "basis": None}, "quality_flags": [],
            "provenance": {"source_id": "http-smoke-fixture", "source_version": "smoke-v1",
                           "source_semantics": "fictitious canonical representation",
                           "adapter_version": "v2", "input_fingerprint": "fixture-" + str(day)},
            "computed_at": (start + timedelta(days=1)).isoformat(),
        },
    }


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(args):
    token = os.environ.get("ANALYTICS_SERVICE_TOKEN", "")
    require(bool(token), "Definir ANALYTICS_SERVICE_TOKEN en esta terminal")
    base = args.base_url.rstrip("/")
    require(base.startswith(("http://", "https://")), "URL HTTP requerida")
    code, health = request(base, "/health", token, authenticated=False)
    require(code == 200, "El servicio no esta READY")
    historical = health["capabilities"]["historical"]
    require(historical["state"] == "READY" and historical["implemented"], "Historico no habilitado")
    require(historical["configuration_id"] == "smoke-only-not-calibrated",
            "Este smoke exige el perfil de fixture; no usar contra un perfil de producto")

    for conditions in (["none"], ["visual"], ["sensory", "mobility_both"]):
        code, resolved = request(base, "/v1/activities/eligibility", token,
                                 {"request_id": "smoke-conditions", "considerations_state": "known",
                                  "conditions": conditions})
        require(code == 200, "Fallo la resolucion del formulario")
        require(resolved["eligibility_state"] == ("known" if conditions == ["none"] else "unknown"),
                "El formulario invento elegibilidad")
        if conditions != ["none"]:
            require("eligibility" not in resolved and resolved["reason"] == "functional_mapping_required",
                    "Faltantes funcionales convertidos en filtros")
    print("PASS: formulario explicito, combinaciones y abstencion funcional")

    if args.phase == "seed":
        require(not args.receipt_file.exists(), "El archivo de resultados ya existe; usar replay")
        subject = "smoke-device-" + uuid4().hex
        rows = []
        for day, value in enumerate([90, 100, 110, 100, 400]):
            payload = representation(day, value, subject)
            code, result = request(base, "/v1/historical/evaluate", token, payload)
            require(code == 200 and result["status"] == "processed" and not result["replayed"],
                    "No se proceso una entrada nueva")
            evaluation = result["result"]["evaluation"]
            require(evaluation["reference_history_count"] == day, "Referencia no prequential")
            require(evaluation["outcome"] == ("ABSTAIN" if day < 3 else "NO_CHANGE" if day == 3 else "CHANGE"),
                    "Resultado de fixture inesperado")
            rows.append({"request": payload, "result": result["result"]})
        require(rows[-1]["result"]["emission"]["decision"] == "EMIT", "Falta evento de cruce del fixture")
        saved = {"fixture_only": True, "configuration_fingerprint": historical["configuration_fingerprint"],
                 "rows": rows}
        args.receipt_file.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt_file.open("x", encoding="utf-8") as stream:
            json.dump(saved, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print("PASS: cold start, NO_CHANGE y cruce con evento guardados (fixture)")
    else:
        saved = json.loads(args.receipt_file.read_text(encoding="utf-8"))
        require(saved.get("fixture_only") is True, "Archivo ajeno a este smoke")
        require(saved["configuration_fingerprint"] == historical["configuration_fingerprint"],
                "Cambio la configuracion")
        rows = saved["rows"]

    for row in rows:
        payload = json.loads(json.dumps(row["request"]))
        payload["request_id"] = "retry-" + uuid4().hex
        payload["representation"]["computed_at"] = datetime.now(timezone.utc).isoformat()
        code, repeated = request(base, "/v1/historical/evaluate", token, payload)
        require(code == 200 and repeated["replayed"] and repeated["result"] == row["result"],
                "El reintento no recupero exactamente el resultado original")
    print("PASS: reintentos conservan evaluacion, evento, fechas y estado originales")

    conflict = json.loads(json.dumps(rows[-1]["request"]))
    conflict["representation"]["value"] += 1
    code, result = request(base, "/v1/historical/evaluate", token, conflict)
    require(code == 409 and result["error"] == "representation_conflict", "Falta rechazo del reintento incompatible")
    code, _ = request(base, "/v1/historical/evaluate", token, rows[0]["request"], authenticated=False)
    require(code == 401, "Falta autenticacion")
    activities = {"request_id": "smoke-activities", "context": "voluntary", "eligibility_state": "unknown"}
    code, result = request(base, "/v1/activities/select", token, activities)
    require(code == 200 and result["reason"] == "eligibility_unknown", "Actividades no coexiste como se esperaba")
    print("PASS: conflicto 409, autenticacion 401 y coexistencia con actividades")
    if args.phase == "replay":
        print("PASS: replay completado; si se reinicio el servicio, verifica recuperacion durable")
    print("RESULTADOS: " + str(args.receipt_file.resolve()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("seed", "replay"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8767")
    parser.add_argument("--receipt-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
