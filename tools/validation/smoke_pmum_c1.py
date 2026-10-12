"""Comprueba HTTP PMUM y coexistencia C1; sólo perfil histórico ficticio aislado."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.validation.smoke_analytics_historical import request, require


def run(base):
    token = os.environ.get("ANALYTICS_SERVICE_TOKEN", "")
    code, health = request(base, "/health", token, authenticated=False)
    require(
        code == 200 and health["capabilities"]["pmum"]["state"] == "READY",
        "PMUM no disponible",
    )
    require(
        health["capabilities"]["historical"]["configuration_id"]
        == "smoke-only-not-calibrated",
        "No ejecutar contra un repositorio de producto",
    )
    payload = {
        "age": 9,
        "sex_code": 1,
        "weekday_category": 2,
        "weekend_category": 3,
        "respondent": "parent_or_caregiver",
        "reference_days": 30,
    }
    code, result = request(base, "/experimental/pmum-estimate", token, payload)
    require(
        code == 200
        and result["status"] == "estimated"
        and result["estimated_pmum_sf_mean"] == 2.6959
        and result["experimental"] is True
        and result["use"] == "internal_research_only",
        "Estimacion de referencia incompatible",
    )
    for key, value, reason in [
        ("age", 5, "invalid_feature_value"),
        ("sex_code", None, "invalid_feature_value"),
        ("weekday_category", None, "missing_parent_answer"),
        ("age", 10**400, "invalid_feature_value"),
        ("age", -(10**400), "invalid_feature_value"),
    ]:
        code, abstention = request(
            base, "/experimental/pmum-estimate", token, {**payload, key: value}
        )
        require(
            code == 200 and abstention == {"status": "unavailable", "reason": reason},
            "Abstencion funcional incompatible",
        )
    code, _ = request(
        base, "/experimental/pmum-estimate", token, payload, authenticated=False
    )
    require(code == 401, "Falta autenticacion")
    return {
        "status": "PASS",
        "reference_score": result["estimated_pmum_sf_mean"],
        "pmum_ready": True,
        "historical_smoke_ready": True,
        "abstention_cases": 5,
        "unauthenticated_status": code,
        "clinical_or_external_validation": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = run(a.base_url.rstrip("/"))
        with a.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2)
            out.write("\n")
        print("PASS: PMUM HTTP y C1 ficticio disponibles; no es validacion externa")
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
