"""Verifica el candidato HU en otro equipo sin depender del adaptador HTTP.

Uso: python experiments/hu_pmum_artifact_check_v2.py DIRECTORIO_DEL_MODELO
"""

import argparse
import json
from pathlib import Path

import joblib

from hu_pmum_candidate_v1 import (EXPECTED_SHA256, FEATURES, MODEL_VERSION,
                                  predict, row_for_model)


def verify(directory):
    model_path = directory / f"{MODEL_VERSION}.joblib"
    manifest_path = directory / f"{MODEL_VERSION}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = joblib.load(model_path)  # Usar solo el archivo local entrenado por nosotros.

    if not (manifest["model_version"] == artifact["version"] == MODEL_VERSION):
        raise ValueError("Versiones incompatibles")
    if not (manifest["source_sha256"] == artifact["source_sha256"] == EXPECTED_SHA256):
        raise ValueError("Fuente incompatible")
    if not (tuple(manifest["features"]) == tuple(artifact["features"]) == FEATURES):
        raise ValueError("Contrato de entradas incompatible")
    if not (manifest["n_trained"] == artifact["trained_rows"] == 803):
        raise ValueError("Cantidad de niños entrenados inesperada")

    reference = predict(model_path, 9, 1, 2, 3)["estimated_pmum_sf_mean"]
    if abs(reference - 2.6959) > 0.0001:
        raise ValueError(f"La predicción de referencia cambió: {reference}")

    invalid_cases = ((9, 1, 2, None), (9, 4, 2, 3), (9, 1, 8, 3), (13, 1, 2, 3))
    for values in invalid_cases:
        try:
            row_for_model(*values)
        except ValueError:
            continue
        raise ValueError(f"Se aceptó una entrada inválida: {values}")

    for sex in (1, 2):
        for weekday in range(1, 6):
            scores = [predict(model_path, 9, sex, weekday, weekend)["estimated_pmum_sf_mean"]
                      for weekend in range(1, 6)]
            if scores != sorted(scores):
                raise ValueError("La predicción baja al aumentar el fin de semana")
        for weekend in range(1, 6):
            scores = [predict(model_path, 9, sex, weekday, weekend)["estimated_pmum_sf_mean"]
                      for weekday in range(1, 6)]
            if scores != sorted(scores):
                raise ValueError("La predicción baja al aumentar el día hábil")

    return {"status": "PASS", "model_version": MODEL_VERSION,
            "n_trained": 803, "reference_prediction": reference,
            "invalid_inputs_rejected": True, "monotonicity_spot_check": True,
            "scope": "technical artifact check only; not external validation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
