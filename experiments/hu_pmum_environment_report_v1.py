"""Imprime procedencia técnica del artefacto sin leer datos individuales.

Uso: python experiments/hu_pmum_environment_report_v1.py DIRECTORIO_DEL_MODELO
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy
import scipy
import sklearn

from hu_pmum_candidate_v1 import EXPECTED_SHA256, MODEL_VERSION


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def report(directory):
    path = directory / f"{MODEL_VERSION}.joblib"
    manifest_path = directory / f"{MODEL_VERSION}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["source_sha256"] != EXPECTED_SHA256 or manifest["n_trained"] != 803:
        raise ValueError("Manifiesto inesperado")
    return {"model_version": MODEL_VERSION,
            "artifact_sha256": sha256(path),
            "training_zip_sha256": EXPECTED_SHA256,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": numpy.__version__, "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__, "joblib": joblib.__version__,
            "contains_child_rows": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.directory), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
