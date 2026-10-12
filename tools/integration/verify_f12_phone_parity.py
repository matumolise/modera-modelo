"""Compara reporte Kotlin y paquete preparado; no certifica captura física."""

import argparse
from datetime import datetime
from hashlib import sha256
import math
import re
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.f12_export import prepare_android_export
from analytics_service.json_codec import strict_json
from analytics_service.f12_bridge import canonical_hash


def _verify_packet_manifest(packet):
    manifest = packet / "SHA256SUMS.txt"
    if manifest.is_symlink() or manifest.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Manifiesto de paquete incompatible")
    expected, total_bytes = {}, 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        relative = Path(name)
        if (separator != "  " or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not name or "\\" in name or relative.is_absolute()
                or any(p in {".", ".."} for p in name.split("/")) or name in expected
                or name == "SHA256SUMS.txt" or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)):
            raise ValueError("Entrada de manifiesto incompatible")
        path = packet / relative
        if not path.resolve().is_relative_to(packet.resolve()) or any(
                p.is_symlink() for p in (path, *(packet / p for p in relative.parents))):
            raise ValueError("Ruta de paquete no permitida")
        if not path.is_file():
            raise ValueError("Archivo del paquete ausente")
        total_bytes += path.stat().st_size
        if total_bytes > 256 * 1024 * 1024:
            raise ValueError("Paquete archivado excesivo")
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Archivo del paquete alterado o ausente")
        expected[name] = digest
    required = {"binding.original.json", "preparation.json", "request.json", "lineage.json"}
    actual = {p.relative_to(packet).as_posix() for p in packet.rglob("*") if p.is_file()} - {"SHA256SUMS.txt"}
    if not required <= set(expected) or set(expected) != actual:
        raise ValueError("Inventario del paquete incompleto o desconocido")
    return expected


def load_packet(packet):
    """Reconstruye desde los originales, no confía solo en request.json."""
    packet = Path(packet)
    expected = _verify_packet_manifest(packet)
    def read_snapshot(name):
        data = (packet / name).read_bytes()
        if name not in expected or sha256(data).hexdigest() != expected[name]:
            raise ValueError("Paquete cambio durante la lectura")
        return data
    binding = strict_json(read_snapshot("binding.original.json"))
    lineage = strict_json(read_snapshot("lineage.json"))
    pairs = []
    for row in lineage["originals"]:
        run_id = row["collector_run_id"]
        if not isinstance(run_id, str) or str(UUID(run_id)) != run_id or UUID(run_id).version != 4:
            raise ValueError("Identidad de consulta incompatible")
        original = "originals/" + run_id + "/"
        pairs.append((read_snapshot(original + "summary.json"), read_snapshot(original + "events.jsonl")))
    rebuilt = prepare_android_export(binding, pairs)
    request = strict_json(read_snapshot("request.json"))
    preparation = strict_json(read_snapshot("preparation.json"))
    if (canonical_hash(rebuilt["request"]) != canonical_hash(request)
            or canonical_hash(rebuilt["audit"]) != canonical_hash(lineage)
            or canonical_hash(rebuilt["preparation"]) != canonical_hash(preparation)):
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
