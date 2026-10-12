"""Ejecuta el harness instalado en un teléfono y recupera sus bytes originales.

No instala ni cambia permisos. No envía información a un servidor.
"""

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

PACKAGE = "ar.edu.uade.modera.f12diagnostic"
TEST = PACKAGE + ".CollectorExportParityTest"
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from analytics_service.f12_bridge import _zone


def capture(args):
    if date.fromisoformat(args.local_date).isoformat() != args.local_date:
        raise ValueError("Fecha local no canonica")
    _zone(args.time_zone)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", args.serial):
        raise ValueError("Serial ADB incompatible")
    if args.query_begin >= args.query_end:
        raise ValueError("Ventana de consulta vacia")
    if args.output_dir.exists():
        raise ValueError("La carpeta de evidencia ya existe; no se sobrescribe")
    def adb(*parts):
        completed = subprocess.run([args.adb, "-s", args.serial, *map(str, parts)],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if completed.returncode:
            raise RuntimeError("ADB fallo: " + completed.stderr[-1500:])
        return completed.stdout
    if adb("get-state").strip() != "device":
        raise RuntimeError("Telefono no autorizado o no accesible")
    if args.serial.startswith("emulator-") or adb("shell", "getprop", "ro.kernel.qemu").strip() == "1":
        raise RuntimeError("Este protocolo exige un telefono fisico, no un emulador")
    args.output_dir.mkdir()
    properties = {key: adb("shell", "getprop", key).strip() for key in
                  ("ro.build.version.sdk", "ro.build.fingerprint", "ro.product.manufacturer",
                   "ro.product.model", "persist.sys.timezone")}
    log = adb("shell", "am", "instrument", "-w", "-r", "-e", "class", TEST,
              "-e", "f12BeginEpochMs", args.query_begin, "-e", "f12EndEpochMs", args.query_end,
              "-e", "f12LocalDate", args.local_date, "-e", "f12TimeZone", args.time_zone,
              PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner")
    (args.output_dir / "instrumentation.log").write_text(log, encoding="utf-8")
    matches = re.findall(r"F12_PARITY_REPORT=(/[^\r\n]+/parity_([0-9a-f]{32})\.json)", log)
    runs = re.findall(r"F12_EXPORT_RUN=([0-9a-f-]{36})", log)
    directories = re.findall(r"F12_EXPORT_DIRECTORY=(/[^\r\n]+)", log)
    passed = len(matches) == 1 and "FAILURES" not in log and "INSTRUMENTATION_FAILED" not in log and "OK (1 test)" in log
    if len(runs) != 1 or len(directories) != 1:
        raise RuntimeError("El harness no aprobo/exporto un caso; conservar instrumentation.log")
    safe_id = runs[0].replace("-", "")
    if not re.fullmatch(r"[0-9a-f]{32}", safe_id):
        raise RuntimeError("UUID del export incompatible")
    # Solo rutas privadas de la app diagnostic; no aceptar comandos del log.
    directory = directories[0]
    allowed = re.fullmatch(r"/(?:storage/emulated/[0-9]+|sdcard)/Android/data/"
                           + re.escape(PACKAGE) + r"/files/f12-diagnostic", directory)
    if allowed is None:
        raise RuntimeError("Ruta de export no recuperable por adb pull; revisar sin inventar evidencia")
    downloads = [("summary_" + safe_id + ".json", "summary.json"),
                 ("events_" + safe_id + ".jsonl", "events.jsonl")]
    if passed:
        if matches[0] != (directory + "/parity_" + safe_id + ".json", safe_id):
            raise RuntimeError("Reporte de paridad asociado a otro export")
        downloads.append(("parity_" + safe_id + ".json", "parity.json"))
    for remote, local in downloads:
        adb("pull", directory + "/" + remote, args.output_dir / local)
    files = {path.name: sha256(path.read_bytes()).hexdigest() for path in args.output_dir.iterdir() if path.is_file()}
    (args.output_dir / "capture_metadata.json").write_text(json.dumps({
        "schema": "f12-phone-capture-evidence-v1", "adb_serial": args.serial,
        "properties": properties, "file_sha256": files,
        "instrumentation_passed": passed,
        "physical_manual_review": "PENDING", "backend_identity_verified": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError("Harness fallido: originales recuperados; paridad pendiente. Conservar evidencia.")
    print("PASS: harness ejecutado y originales recuperados. Falta preparar y verificar paridad/manual.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--query-begin", type=int, required=True)
    parser.add_argument("--query-end", type=int, required=True)
    parser.add_argument("--local-date", required=True)
    parser.add_argument("--time-zone", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        capture(args)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
