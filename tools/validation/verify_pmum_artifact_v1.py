"""Verifica HU v1 entregado sin entrenar, modificar ni sustituir el artefacto."""

import argparse
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from analytics_service.pmum import CachedPmum, ModelUnavailable
from analytics_service.settings import Settings
from experiments.hu_pmum_candidate_v1 import MODEL_VERSION

EXPECTED_ARTIFACT_SHA256 = (
    "56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0"
)


def verify(directory):
    model = directory / (MODEL_VERSION + ".joblib")
    manifest = directory / (MODEL_VERSION + ".json")
    model_bytes = model.read_bytes()
    manifest_bytes = manifest.read_bytes()
    if sha256(model_bytes).hexdigest() != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("No coincide el artefacto registrado; no cargarlo")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        cached = CachedPmum(
            Settings(
                token="offline-artifact-verification-only",
                pmum_enabled=True,
                model_path=model,
                manifest_path=manifest,
                model_sha256=EXPECTED_ARTIFACT_SHA256,
            )
        )
        pipeline = cached._model
        if (
            getattr(pipeline, "n_features_in_", None) != 4
            or not hasattr(pipeline, "named_steps")
            or float(pipeline.named_steps["ridge"].alpha) != 1.0
        ):
            raise ValueError("Pipeline no corresponde al Ridge fijo de cuatro entradas")
        encoder = pipeline.named_steps["columntransformer"].named_transformers_[
            "categories"
        ]
        expected = [["1", "2"], ["1", "2", "3", "4", "5"], ["1", "2", "3", "4", "5"]]
        if [list(v) for v in encoder.categories_] != expected:
            raise ValueError("Codificacion de categorias incompatible")
        scores = []
        for age in range(6, 13):
            for sex in (1, 2):
                for weekday in range(1, 6):
                    for weekend in range(1, 6):
                        result = cached.estimate(
                            {
                                "age": age,
                                "sex_code": sex,
                                "weekday_category": weekday,
                                "weekend_category": weekend,
                                "respondent": "parent_or_caregiver",
                                "reference_days": 30,
                            }
                        )
                        if (
                            result["status"] != "estimated"
                            or not 1 <= result["estimated_pmum_sf_mean"] <= 5
                        ):
                            raise ValueError("Salida del artefacto incompatible")
                        scores.append(result["estimated_pmum_sf_mean"])
        for age in (6.5, 8.5):
            if (
                cached.estimate(
                    {
                        "age": age,
                        "sex_code": 1,
                        "weekday_category": 2,
                        "weekend_category": 3,
                        "respondent": "parent_or_caregiver",
                        "reference_days": 30,
                    }
                )["status"]
                != "estimated"
            ):
                raise ValueError("Edad fraccionaria del dominio fuente rechazada")
    if model.read_bytes() != model_bytes or manifest.read_bytes() != manifest_bytes:
        raise ValueError("Artefacto/manifiesto cambiaron durante la verificacion")
    return {
        "status": "PASS",
        "scope": "artifact_contract_and_numeric_grid_not_external_validation",
        "model_version": MODEL_VERSION,
        "artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "grid_cases": len(scores),
        "fractional_age_checks": 2,
        "prediction_min": min(scores),
        "prediction_max": max(scores),
        "original_files_unchanged": True,
        "new_model_trained": False,
        "runtime": {
            n: metadata.version(n) for n in ["scikit-learn", "numpy", "scipy", "joblib"]
        },
        "load_warnings": [
            {"category": w.category.__name__, "message": str(w.message)}
            for w in captured
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = verify(a.model_dir)
        with a.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2)
            out.write("\n")
        print("PASS: HU v1 registrado verificado; originales sin cambios")
        return 0
    except (OSError, ValueError, KeyError, TypeError, ModelUnavailable) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
