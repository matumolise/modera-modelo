"""Ensayo HTTP en proceso real con el artefacto PMUM original, sin entrenarlo.

Utiliza perfiles, respuestas, eventos y acuses ficticios. No certifica captura
Android, integración del backend, despliegue AWS ni eficacia de las actividades.
"""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import itertools
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.child_offers import ChildOfferCoordinator, POLICY
from analytics_service.child_offer_timing import adaptive_policy, timing_from_estimate
from analytics_service.pmum import CachedPmum
from analytics_service.settings import Settings
from experiments.hu_pmum_candidate_v1 import MODEL_VERSION
from tools.validation.verify_pmum_artifact_v1 import EXPECTED_ARTIFACT_SHA256


def verify(model_dir, output_dir, minimum_minutes, maximum_minutes, *, expected_sha256=EXPECTED_ARTIFACT_SHA256):
    """El override del hash es exclusivo del test controlado que importa esta función.

    La CLI utiliza siempre la huella original registrada, sin opción de override.
    """
    model_dir, output_dir = Path(model_dir).resolve(), Path(output_dir).resolve()
    model = model_dir / (MODEL_VERSION + ".joblib")
    manifest = model_dir / (MODEL_VERSION + ".json")
    model_hash = sha256(model.read_bytes()).hexdigest()
    manifest_hash = sha256(manifest.read_bytes()).hexdigest()
    if model_hash != expected_sha256:
        raise ValueError("No coincide el artefacto esperado; no se cargará ni sustituirá")
    policy = adaptive_policy(POLICY, minimum_minutes, maximum_minutes)
    token = secrets.token_hex(24)
    wrapper = CachedPmum(Settings(token=token, pmum_enabled=True, model_path=model,
                                  manifest_path=manifest, model_sha256=model_hash))
    candidates = []
    # Dieciséis combinaciones válidas para encontrar dos estimaciones diferentes.
    # No se presupone que aumentar horas de pantalla aumente siempre la predicción.
    for age, sex, weekday, weekend in itertools.product((6, 12), (1, 2), (1, 5), (1, 5)):
        answers = {"age": age, "sex_code": sex, "weekday_category": weekday,
                   "weekend_category": weekend, "respondent": "parent_or_caregiver", "reference_days": 30}
        prediction = {**wrapper.estimate(answers), "artifact_sha256": wrapper.artifact_sha256}
        candidates.append((timing_from_estimate(prediction, policy["pmum_timing"]), answers))
    candidates.sort(key=lambda case: case[0]["estimated_pmum_sf_mean"])
    cases = {"lower": candidates[0], "higher": candidates[-1]}
    if cases["lower"][0]["cooldown_minutes"] <= cases["higher"][0]["cooldown_minutes"]:
        raise ValueError("Las predicciones no permiten demostrar esperas diferentes")
    midpoint = sum(case[0]["cooldown_minutes"] for case in cases.values()) / 2
    # El escenario se mantiene en la ventana diurna para no confundir guardas.
    if midpoint >= 540:
        raise ValueError("Este ensayo diurno requiere una espera intermedia menor de nueve horas")
    output_dir.mkdir(parents=True, exist_ok=False)
    state = output_dir / "fictitious-coordinator.sqlite"
    ChildOfferCoordinator(state, create=True, policy=policy)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    env = {key: value for key, value in os.environ.items() if not key.startswith("ANALYTICS_")}
    env.update({"ANALYTICS_SERVICE_TOKEN": token, "ANALYTICS_HOST": "127.0.0.1",
                "ANALYTICS_PORT": str(port), "ANALYTICS_PMUM_ENABLED": "true",
                "ANALYTICS_ACTIVITIES_ENABLED": "true", "ANALYTICS_HISTORICAL_ENABLED": "false",
                "ANALYTICS_ADULT_MESSAGES_ENABLED": "false", "ANALYTICS_CHILD_OFFERS_ENABLED": "true",
                "ANALYTICS_MODEL_PATH": str(model), "ANALYTICS_MODEL_MANIFEST_PATH": str(manifest),
                "ANALYTICS_MODEL_SHA256": model_hash, "ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH": str(state),
                "ANALYTICS_CHILD_OFFERS_PMUM_MIN_MINUTES": str(minimum_minutes),
                "ANALYTICS_CHILD_OFFERS_PMUM_MAX_MINUTES": str(maximum_minutes)})

    def request(path, payload=None):
        headers = {"Authorization": "Bearer " + token}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(base_url + path, data=data, headers=headers), timeout=10) as response:
            return json.load(response)

    process = None
    log = (output_dir / "server.log").open("w", encoding="utf-8")

    def start():
        nonlocal process
        process = subprocess.Popen([sys.executable, str(ROOT / "analytics_api.py")],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("El servidor terminó antes de estar disponible; revisar server.log")
            try:
                if request("/health")["status"] == "ready":
                    return
            except (OSError, ValueError):
                time.sleep(0.1)
        raise RuntimeError("El servidor no alcanzó disponibilidad")

    def stop():
        nonlocal process
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process = None

    base = datetime.fromisoformat("2026-10-16T09:00:00-03:00")
    def evaluation(name, answers, at, interval, request_id):
        return {"request_id": request_id, "pmum_parent_answers": answers, "evidence": {
            "profile_id": "fictitious-pmum-" + name, "series_id": "fictitious-series-" + name,
            "interval_id": interval, "now": at.isoformat(),
            "interval_started_at": (at - timedelta(minutes=60)).isoformat(),
            "bedtime_at": at.replace(hour=23, minute=0, second=0).isoformat(),
            "automatic_enabled": True, "assignment_verified": True, "shared_phone": False,
            "capture_verified": True, "screen_interactive": True, "game_active": False,
            "in_school_period": False, "eligibility_state": "known", "eligibility": {}, "interests": []}}

    receipts, histories = [], {}
    try:
        start()
        for name, (timing, answers) in cases.items():
            payload = evaluation(name, answers, base, "first", name + "-first")
            original = request("/v2/child-offers/evaluate", payload)
            assert original["offer"]["timing"]["cooldown_minutes"] == timing["cooldown_minutes"]
            receipts.append(("/v2/child-offers/evaluate", payload, original))
            for event in ("delivered", "postponed"):
                body = {"request_id": name + "-" + event, "profile_id": payload["evidence"]["profile_id"],
                        "offer_id": original["offer"]["offer_id"], "event": event,
                        "occurred_at": base.isoformat(), "now": base.isoformat()}
                if event == "delivered":
                    body["channel"] = "overlay"
                receipts.append(("/v1/child-offers/events", body, request("/v1/child-offers/events", body)))
            histories[name] = request("/v1/child-offers/profiles/" + payload["evidence"]["profile_id"] + "/history")
        stop()
        start()
        for path, body, original in receipts:
            replay = request(path, body)
            assert replay == {**original, "replayed": True}, "El recibo original cambió"
        decisions = {}
        for name, (_, answers) in cases.items():
            profile = "fictitious-pmum-" + name
            assert request("/v1/child-offers/profiles/" + profile + "/history") == histories[name]
            body = evaluation(name, answers, base + timedelta(minutes=midpoint), "second", name + "-second")
            decisions[name] = request("/v2/child-offers/evaluate", body)
        assert decisions["lower"]["reason"] == "shared_cooldown"
        assert decisions["higher"]["status"] == "offer"
        assert sha256(model.read_bytes()).hexdigest() == model_hash
        assert sha256(manifest.read_bytes()).hexdigest() == manifest_hash
        report = {"status": "PASS", "scope": "controlled_profiles_real_process_model_to_coordinator",
                  "original_registered_model": model_hash == EXPECTED_ARTIFACT_SHA256,
                  "model_sha256": model_hash, "manifest_sha256": manifest_hash,
                  "model_files_unchanged": True, "trained_model": False, "policy": policy,
                  "corner_predictions_checked": len(candidates),
                  "compared_cases": {name: {"timing": timing, "parent_answers": answers}
                                     for name, (timing, answers) in cases.items()},
                  "replayed_original_receipts": len(receipts), "histories_preserved": True,
                  "decisions_at_same_elapsed_minutes": {"minutes": midpoint, "results": decisions},
                  "real_android_backend_aws_validated": False}
        (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report
    finally:
        stop()
        log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-minutes", type=int, required=True)
    parser.add_argument("--maximum-minutes", type=int, required=True)
    args = parser.parse_args()
    try:
        verify(args.model_dir, args.output_dir, args.minimum_minutes, args.maximum_minutes)
    except (OSError, ValueError, RuntimeError, AssertionError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print("PASS: modelo original -> espera -> ofertas; HTTP, reinicio y reintentos. Perfiles ficticios, sin validación Android/AWS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
