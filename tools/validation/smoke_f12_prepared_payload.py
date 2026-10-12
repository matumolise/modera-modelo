"""Envía un paquete preparado a un histórico LOCAL SMOKE_ONLY y prueba replay.

No aprueba el export físico ni autoriza su uso con familias.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.json_codec import strict_json
from tools.integration.verify_f12_phone_parity import load_packet
from tools.validation.smoke_analytics_historical import request, require


def run(args):
    url = urlparse(args.base_url)
    require(url.scheme == "http" and url.hostname == "127.0.0.1" and not url.username
            and not url.password and url.path in {"", "/"} and not url.query and not url.fragment,
            "Este ensayo solo permite http://127.0.0.1:PUERTO")
    base = args.base_url.rstrip("/")
    token = os.environ.get("ANALYTICS_SERVICE_TOKEN", "")
    require(bool(token), "Definir el token del servicio aislado en esta terminal")
    _, _, payload = load_packet(args.packet)
    fingerprint = sha256((args.packet / "request.json").read_bytes()).hexdigest()
    code, health = request(base, "/health", token, authenticated=False)
    require(code == 200, "Historico local no esta READY")
    capability = health["capabilities"]["historical"]
    require(capability["state"] == "READY" and capability["configuration_id"] == "smoke-only-not-calibrated",
            "No usar este ensayo con un perfil C1 de producto")
    require(health["capabilities"]["pmum"]["state"] == "DISABLED", "Deshabilitar PMUM en este ensayo")
    if args.phase == "replay":
        saved = strict_json(args.receipt_file.read_bytes())
        require(saved["request_sha256"] == fingerprint, "El payload cambio; no es un reintento")
        require(saved["configuration_fingerprint"] == capability["configuration_fingerprint"], "Cambio C1")
    else:
        require(not args.receipt_file.exists(), "El recibo ya existe; usar replay")
        require(args.receipt_file.parent.is_dir(), "Crear antes el directorio del recibo fuera de Git")
    code, response = request(base, "/v1/historical/evaluate", token, payload)
    require(code == 200 and response["status"] == "processed", "El historico no reconocio el payload")
    if args.phase == "seed":
        saved = {"scope": "technical-smoke-only-not-calibrated", "physical_validation": "PENDING",
                 "seed_response_replayed": response["replayed"],
                 "request_sha256": fingerprint, "configuration_fingerprint": capability["configuration_fingerprint"],
                 "request": payload, "result": response["result"]}
        with args.receipt_file.open("x", encoding="utf-8") as stream:
            json.dump(saved, stream, ensure_ascii=False, allow_nan=False, indent=2); stream.write("\n")
        print("PASS: payload reconocido; recibo original conservado, sin aprobacion fisica.")
    else:
        require(response["replayed"] and response["result"] == saved["result"], "No se recupero el recibo original")
        print("PASS: reintento recupera el resultado original; declarar reinicio solo si se ejecuto.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("seed", "replay"), required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8769")
    parser.add_argument("--receipt-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
