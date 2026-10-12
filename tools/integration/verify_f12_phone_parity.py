"""Compara reporte Kotlin y paquete preparado; no certifica captura física."""

import argparse
from datetime import datetime
from hashlib import sha256
import math
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.f12_export import prepare_android_export
from analytics_service.json_codec import strict_json


def load_packet(packet):
    """Reconstruye desde los originales, no confía solo en request.json."""
    packet = Path(packet)
    binding = strict_json((packet / "binding.original.json").read_bytes())
    lineage = strict_json((packet / "lineage.json").read_bytes())
    pairs = []
    for row in lineage["originals"]:
        run_id = row["collector_run_id"]
        if str(UUID(run_id)) != run_id:
            raise ValueError("Identidad de consulta incompatible")
        original = packet / "originals" / run_id
        pairs.append(((original / "summary.json").read_bytes(), (original / "events.jsonl").read_bytes()))
    rebuilt = prepare_android_export(binding, pairs)
    request = strict_json((packet / "request.json").read_bytes())
    if rebuilt["request"] != request or rebuilt["audit"] != lineage:
        raise ValueError("Paquete preparado alterado o version de herramienta distinta")
    return binding, lineage, request


def verify(report, packet):
    if not isinstance(report, dict) or set(report) != {
        "reportSchema", "collectorRunId", "summarySha256", "eventsSha256", "localDate", "timeZone",
        "phoneTimeZone", "intervalBeginEpochMs", "intervalEndEpochMs", "status", "durationMs",
        "manualCaptureValidation",
    } or report["reportSchema"] != "f12-phone-parity-v1" or report["manualCaptureValidation"] != "PENDING":
        raise ValueError("Reporte del harness incompatible")
    packet = Path(packet)
    binding, lineage, request = load_packet(packet)
    originals = lineage["originals"]
    if len(originals) != 1 or originals[0]["collector_run_id"] != report["collectorRunId"]:
        raise ValueError("Este reporte de paridad requiere una sola consulta original")
    if str(UUID(report["collectorRunId"])) != report["collectorRunId"]:
        raise ValueError("Identidad de consulta del reporte incompatible")
    original = packet / "originals" / originals[0]["collector_run_id"]
    pair = ((original / "summary.json").read_bytes(), (original / "events.jsonl").read_bytes())
    if (sha256(pair[0]).hexdigest() != report["summarySha256"]
            or sha256(pair[1]).hexdigest() != report["eventsSha256"]):
        raise ValueError("Los originales no coinciden con los bytes del telefono")
    if (report["localDate"] != binding["local_date"] or report["timeZone"] != binding["series"]["time_zone"]
            or report["phoneTimeZone"] != report["timeZone"]):
        raise ValueError("Fecha/zona del telefono y backend distintas; revisar explicitamente")
    rep = request["representation"]
    for field, key in (("interval_start", "intervalBeginEpochMs"), ("interval_end", "intervalEndEpochMs")):
        if type(report[key]) is not int or report[key] != int(datetime.fromisoformat(rep[field]).timestamp() * 1000):
            raise ValueError("Limites diarios no coinciden entre Kotlin y Python")
    if report["status"] != rep["status"]:
        raise ValueError("Estado de reconstruccion no coincide")
    duration = report["durationMs"]
    if rep["status"] == "MISSING":
        if duration is not None or rep["value"] is not None:
            raise ValueError("Ausencia transformada en duracion")
    elif type(duration) is not int or duration < 0 or not math.isclose(
            rep["value"] * 60000, duration, rel_tol=0, abs_tol=0.001):
        # Tolerancia computacional de 1 microsegundo, NO umbral de captura/C1.
        raise ValueError("Duracion reconstruida no coincide")
    return {"status": "PASS", "scope": "same-bytes-kotlin-python-reconstruction",
            "physical_capture_validation": "PENDING", "collector_run_id": report["collectorRunId"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(strict_json(args.report.read_bytes()), args.packet)
        print("PASS: paridad de bytes, limites, estado y duracion Kotlin/Python.")
        print("PENDIENTE: contraste fisico/manual y atribucion por backend.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ImportError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
