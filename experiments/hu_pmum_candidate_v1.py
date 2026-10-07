"""Construir y consultar un candidato PMUM-SF HU sin tocar inferencia de producción.

Entrenar: python experiments/hu_pmum_candidate_v1.py train ZIP_HU DIRECTORIO_SALIDA
Predecir: python experiments/hu_pmum_candidate_v1.py predict MODELO age sex_code weekday_category weekend_category
"""

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from hu_pmum_real_data import load_hungarian, make_ridge


EXPECTED_SHA256 = "f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5"
FEATURES = ("age", "sex_code", "weekday_category", "weekend_category")
MODEL_VERSION = "hu_pmum_sf_experimental_v1"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def integer_category(name, value, allowed):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value not in allowed:
        raise ValueError(f"{name} debe ser uno de {sorted(allowed)}")
    return str(value)


def row_for_model(age, sex_code, weekday_category, weekend_category):
    if isinstance(age, bool) or not isinstance(age, (int, float)) or not math.isfinite(age) or not 6 <= age <= 12:
        raise ValueError("age debe ser un número finito entre 6 y 12 años")
    return np.asarray([[float(age),
                        integer_category("sex_code", sex_code, {1, 2}),
                        integer_category("weekday_category", weekday_category, {1, 2, 3, 4, 5}),
                        integer_category("weekend_category", weekend_category, {1, 2, 3, 4, 5})]],
                      dtype=object)


def train(zip_path, output_dir):
    if sha256(zip_path) != EXPECTED_SHA256:
        raise ValueError("La base de entrenamiento difiere del ZIP auditado")
    x, y, _ = load_hungarian(zip_path)
    included = np.isin(x[:, 1], ["1", "2"])
    if included.sum() != 803:
        raise ValueError("Esperábamos 803 niños con códigos de sexo 1 o 2")
    # La regularización se fijó durante el análisis exploratorio anterior.
    model = make_ridge([0, 1, 2, 3], alpha=1).fit(x[included], y[included])
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{MODEL_VERSION}.joblib"
    joblib.dump({"model": model, "version": MODEL_VERSION,
                 "features": FEATURES, "source_sha256": EXPECTED_SHA256,
                 "sex_codes": [1, 2], "target": "PMUMTotal/9",
                 "trained_rows": int(included.sum())}, artifact_path)
    manifest = {"model_version": MODEL_VERSION, "source": "Zenodo 21802447 / SEM.dat",
                "source_sha256": EXPECTED_SHA256,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "features": FEATURES, "target": "PMUM-SF mean, 1 to 5",
                "n_trained": int(included.sum()), "sex_code_4_excluded": 3,
                "regularization": "Ridge(alpha=1), selected after exploratory evaluation",
                "evaluation": "Nested cross-validation on 803: MAE 0.6427, baseline 0.7430; exploratory, no external validation",
                "deployment_status": "NOT APPROVED; no app integration"}
    (output_dir / f"{MODEL_VERSION}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact_path, manifest


def predict(model_path, age, sex_code, weekday_category, weekend_category):
    # joblib/pickle solo debe cargarse desde un artefacto local de confianza.
    artifact = joblib.load(model_path)
    if artifact.get("version") != MODEL_VERSION or tuple(artifact.get("features", ())) != FEATURES:
        raise ValueError("Versión o contrato de entradas incompatibles")
    row = row_for_model(age, sex_code, weekday_category, weekend_category)
    estimated = float(artifact["model"].predict(row)[0])
    return {"estimated_pmum_sf_mean": round(float(np.clip(estimated, 1, 5)), 4),
            "model_version": MODEL_VERSION, "experimental": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("zip_hu", type=Path)
    train_parser.add_argument("output_dir", type=Path)
    predict_parser = sub.add_parser("predict")
    predict_parser.add_argument("model_path", type=Path)
    predict_parser.add_argument("age", type=float)
    predict_parser.add_argument("sex_code", type=int)
    predict_parser.add_argument("weekday_category", type=int)
    predict_parser.add_argument("weekend_category", type=int)
    args = parser.parse_args()
    if args.action == "train":
        path, manifest = train(args.zip_hu, args.output_dir)
        print(json.dumps({"artifact": str(path), "manifest": manifest}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(predict(args.model_path, args.age, args.sex_code,
                                 args.weekday_category, args.weekend_category),
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
