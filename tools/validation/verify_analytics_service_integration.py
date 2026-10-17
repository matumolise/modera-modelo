"""Ensayo HTTP nativo con datos ficticios, reinicio de proceso y recibos originales."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics_service.child_offers import ChildOfferCoordinator
from tools.validation.demo_adult_messages import payload as adult_payload


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description="Ensayo ficticio del servicio en un proceso local nuevo")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    token = secrets.token_urlsafe(32)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    base = "http://127.0.0.1:" + str(port)
    child_path = output / "fictitious-child-offers.sqlite"
    ChildOfferCoordinator(child_path, create=True)
    env = {**os.environ,
           "ANALYTICS_SERVICE_TOKEN": token, "ANALYTICS_HOST": "127.0.0.1", "ANALYTICS_PORT": str(port),
           "ANALYTICS_PMUM_ENABLED": "false", "ANALYTICS_ACTIVITIES_ENABLED": "true",
           "ANALYTICS_HISTORICAL_ENABLED": "true",
           "ANALYTICS_HISTORICAL_CONFIG_PATH": str(ROOT / "tests/fixtures/historical_c1_smoke_only.json"),
           "ANALYTICS_HISTORICAL_REPOSITORY_PATH": str(output / "fictitious-history.json"),
           "ANALYTICS_ADULT_MESSAGES_ENABLED": "true",
           "ANALYTICS_ADULT_MESSAGES_REPOSITORY_PATH": str(output / "fictitious-messages.sqlite"),
           "ANALYTICS_CHILD_OFFERS_ENABLED": "true",
           "ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH": str(child_path)}

    def request(path, payload=None, expected=200, authenticated=True):
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + token
        req = Request(base + path, data=None if payload is None else json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urlopen(req, timeout=5) as response:
                status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        require(status == expected, "Estado HTTP inesperado en " + path + ": " + str(status))
        return json.loads(body)

    def start(log):
        process = subprocess.Popen([sys.executable, str(ROOT / "analytics_api.py")], cwd=ROOT,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(200):
                if process.poll() is not None:
                    raise RuntimeError("El servicio terminó antes de estar disponible")
                try:
                    health = request("/health", authenticated=False)
                    return process, health
                except (URLError, TimeoutError, RuntimeError):
                    time.sleep(0.05)
            raise RuntimeError("El servicio no alcanzó disponibilidad")
        except BaseException:
            process.kill()
            process.wait(timeout=10)
            raise

    evaluation = json.loads((ROOT / "tests/fixtures/integration/child_offer_evaluation_fictitious.json").read_text(encoding="utf-8"))
    historical = json.loads((ROOT / "tests/fixtures/integration/f12_request_synthetic.json").read_text(encoding="utf-8"))
    increase = adult_payload("fictitious-http-increase", [100] * 14 + [140] * 14, 28, "fictitious-adult-increase")
    decrease = adult_payload("fictitious-http-decrease", [140] * 14 + [100] * 14, 28, "fictitious-adult-decrease")
    process = None
    with (output / "service.log").open("w", encoding="utf-8") as log:
        try:
            process, health = start(log)
            require(health["capabilities"]["child_offers"]["state"] == "READY", "Coordinador no disponible")
            require(health["capabilities"]["pmum"]["state"] == "DISABLED", "PMUM debe permanecer deshabilitado")
            request("/v1/child-offers/evaluate", evaluation, expected=401, authenticated=False)
            original_child = request("/v1/child-offers/evaluate", evaluation)
            require(original_child["status"] == "offer", "No se generó la oferta ficticia")
            offer = original_child["offer"]
            delivery = {"request_id": "fictitious-http-delivery", "profile_id": offer["profile_id"],
                        "offer_id": offer["offer_id"], "event": "delivered", "channel": "overlay",
                        "occurred_at": evaluation["evidence"]["now"], "now": evaluation["evidence"]["now"]}
            original_delivery = request("/v1/child-offers/events", delivery)
            selection = {**delivery, "request_id": "fictitious-http-selection", "event": "selected",
                         "selected_activity_id": offer["activities_offered"][0]}
            del selection["channel"]
            original_selection = request("/v1/child-offers/events", selection)
            child_history_route = "/v1/child-offers/profiles/" + offer["profile_id"] + "/history"
            current_history = request(child_history_route)
            original_historical = request("/v1/historical/evaluate", historical)
            original_increase = request("/v1/adult-messages/evaluate", increase)
            original_decrease = request("/v1/adult-messages/evaluate", decrease)
            require(original_increase["card"] is not None and original_decrease["card"] is not None, "Falta tarjeta ficticia")
            original_adult_history = request("/v1/adult-messages/profiles/fictitious-http-increase/history")
            # Terminar el proceso después de confirmar las transacciones, sin limpiar sus bases.
            process.kill()
            process.wait(timeout=10)
            process, health_after = start(log)
            require(request("/v1/child-offers/evaluate", evaluation) == {**original_child, "replayed": True}, "Cambió el recibo de evaluación infantil")
            require(request("/v1/child-offers/events", delivery) == {**original_delivery, "replayed": True}, "Cambió el recibo de entrega")
            require(request("/v1/child-offers/events", selection) == {**original_selection, "replayed": True}, "Cambió el recibo de selección")
            require(request(child_history_route) == current_history, "El replay alteró el historial infantil")
            require(request("/v1/historical/evaluate", historical) == {**original_historical, "replayed": True}, "El replay alteró el recibo C1")
            require(request("/v1/adult-messages/evaluate", increase) == {**original_increase, "replayed": True}, "El replay alteró el recibo adulto")
            require(request("/v1/adult-messages/profiles/fictitious-http-increase/history") == original_adult_history, "El replay duplicó versiones adultas")
            conflict = deepcopy(evaluation)
            conflict["evidence"]["game_active"] = True
            request("/v1/child-offers/evaluate", conflict, expected=409)
            returned = request("/v1/adult-messages/evaluate", adult_payload(
                "fictitious-http-increase", [100] * 14 + [140] * 14 + [100] * 14, 42, "fictitious-adult-return"))
            require(returned["status"] == "RESOLVED", "No se registró el retorno ficticio")
            final_history = request(child_history_route)
            require(len(final_history["offers"]) == 1 and len(final_history["events"]) == 3, "Se duplicaron ofertas o eventos")
            report = {"status": "PASS", "evidence": "CONTROLLED_FICTITIOUS_ONLY",
                      "physical_android_validation": False, "backend_juanma_validation": False,
                      "docker_validation": False, "aws_validation": False,
                      "configuration_scope": "C1_SMOKE_ONLY_NOT_PRODUCT_CALIBRATION",
                      "checks": ["authenticated_http", "child_generation_delivery_selection_history",
                                 "process_kill_restart", "original_child_receipts", "original_c1_receipt",
                                 "original_adult_receipt", "no_duplicate_history", "identity_conflict",
                                 "adult_increase_decrease_return"],
                      "health_before": health, "health_after": health_after,
                      "child_offer_id": offer["offer_id"], "child_events": len(final_history["events"]),
                      "requests": {"child_evaluation": evaluation, "delivery": delivery,
                                   "selection": selection, "historical": historical, "adult_increase": increase},
                      "runtime": {"python": sys.version.split()[0]}}
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    print("PASS: HTTP, reinicio de proceso, recibos originales e historiales; evidencia ficticia. Sin validación Docker/AWS/Android.")


if __name__ == "__main__":
    main()
