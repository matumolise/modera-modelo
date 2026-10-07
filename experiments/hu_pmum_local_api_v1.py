"""Servidor HTTP local del modelo HU experimental, solo para integración.

python experiments/hu_pmum_local_api_v1.py --model RUTA_AL_JOBLIB
POST http://127.0.0.1:8765/experimental/pmum-estimate
No incluye autenticación, persistencia ni permisos para desplegarlo públicamente.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hu_pmum_candidate_v1 import MODEL_VERSION
from hu_pmum_parent_adapter_v2 import estimate


class Handler(BaseHTTPRequestHandler):
    model_path: Path

    def log_message(self, format, *args):
        # No escribir payloads o respuestas parentales en el log del prototipo.
        pass

    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/health":
            return self.send_json(404, {"error": "not_found"})
        self.send_json(200, {"status": "up", "model_version": MODEL_VERSION,
                             "experimental": True})

    def do_POST(self):
        if self.path != "/experimental/pmum-estimate":
            return self.send_json(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if not 0 <= length <= 16384:
            return self.send_json(400, {"error": "invalid_content_length"})
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            return self.send_json(415, {"error": "json_content_type_required"})
        try:
            request = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "invalid_json"})
        try:
            response = estimate(self.model_path, request)
        except (FileNotFoundError, OSError, ValueError):
            return self.send_json(503, {"error": "model_unavailable"})
        self.send_json(200, response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error("No se encuentra el modelo: " + str(args.model))
    handler = type("ExperimentalHandler", (Handler,), {"model_path": args.model})
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Experimental PMUM service on http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
