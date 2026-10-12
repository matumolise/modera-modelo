"""Reproduce ajustes de evaluación en memoria; no guarda ni sustituye un modelo de entrega."""

import argparse
import hashlib
import json
from importlib import metadata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import KFold, cross_val_score
from experiments.hu_pmum_candidate_v1 import EXPECTED_SHA256
from experiments.hu_pmum_real_data import load_hungarian, make_ridge, metrics


def index_fingerprint(indices):
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()


def audit(zip_path):
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Fuente distinta del ZIP HU registrado")
    x, y, one_child = load_hungarian(zip_path)
    original_indices = np.flatnonzero(np.isin(x[:, 1], ["1", "2"]))
    x, y, one_child = (
        x[original_indices],
        y[original_indices],
        one_child[original_indices],
    )
    if len(y) != 803:
        raise ValueError("Cohorte HU v1 incompatible")
    prediction = {
        k: np.full(len(y), np.nan)
        for k in ["mean", "median_baseline", "fixed_alpha_1", "nested_selection"]
    }
    folds = []
    for fold, (train, test) in enumerate(
        KFold(5, shuffle=True, random_state=1027).split(x)
    ):
        if set(train) & set(test):
            raise ValueError("Solapamiento train/test")
        inner = KFold(4, shuffle=True, random_state=20261007 + fold)
        scores = {
            str(a): float(
                -cross_val_score(
                    make_ridge([0, 1, 2, 3], a),
                    x[train],
                    y[train],
                    cv=inner,
                    scoring="neg_mean_absolute_error",
                ).mean()
            )
            for a in [1, 10, 100]
        }
        alpha = min((score, int(a)) for a, score in scores.items())[1]
        prediction["mean"][test] = np.clip(
            DummyRegressor(strategy="mean").fit(x[train], y[train]).predict(x[test]),
            1,
            5,
        )
        prediction["median_baseline"][test] = np.clip(
            DummyRegressor(strategy="median").fit(x[train], y[train]).predict(x[test]),
            1,
            5,
        )
        prediction["fixed_alpha_1"][test] = np.clip(
            make_ridge([0, 1, 2, 3], 1).fit(x[train], y[train]).predict(x[test]), 1, 5
        )
        prediction["nested_selection"][test] = np.clip(
            make_ridge([0, 1, 2, 3], alpha).fit(x[train], y[train]).predict(x[test]),
            1,
            5,
        )
        folds.append(
            {
                "fold": fold,
                "n_train": len(train),
                "n_test": len(test),
                "selected_alpha": alpha,
                "train_source_indices_sha256": index_fingerprint(
                    original_indices[train]
                ),
                "test_source_indices_sha256": index_fingerprint(original_indices[test]),
                "inner_unclipped_cv_mae": scores,
            }
        )
    if any(not np.isfinite(v).all() for v in prediction.values()):
        raise ValueError("Predicciones OOF incompletas")
    groups = {
        "all": np.ones(len(y), dtype=bool),
        "one_child": one_child,
        "sex_code_1": x[:, 1] == "1",
        "sex_code_2": x[:, 1] == "2",
        "age_6_to_9": x[:, 0].astype(float) < 10,
        "age_10_to_12": x[:, 0].astype(float) >= 10,
    }
    summaries = {
        g: {name: metrics(y[mask], p[mask]) for name, p in prediction.items()}
        for g, mask in groups.items()
    }
    residuals = {}
    for name, p in prediction.items():
        error = np.abs(p - y)
        residuals[name] = {
            "absolute_error_p90": float(np.quantile(error, 0.9)),
            "fraction_error_over_one_scale_point": float((error > 1).mean()),
            "prediction_min": float(p.min()),
            "prediction_max": float(p.max()),
        }
    bins = []
    pred = prediction["fixed_alpha_1"]
    order = np.argsort(pred, kind="stable")
    for b in np.array_split(order, 5):
        bins.append(
            {
                "n": len(b),
                "mean_prediction": float(pred[b].mean()),
                "mean_observed": float(y[b].mean()),
                "mean_absolute_error": float(np.abs(pred[b] - y[b]).mean()),
            }
        )
    return {
        "scope": "exploratory_internal_oof_not_external_validation",
        "source_sha256": digest,
        "n_source_complete": 806,
        "n_included": 803,
        "n_excluded_sex_code_4": 3,
        "source_index_order_sha256": index_fingerprint(original_indices),
        "folds": folds,
        "metrics": summaries,
        "error_diagnostics": residuals,
        "fixed_alpha_1_prediction_bins_descriptive": bins,
        "fixed_alpha_was_selected_after_prior_exploration": True,
        "nested_metrics_describe_selection_procedure_not_single_fitted_artifact": True,
        "inner_selection_uses_unclipped_predictions_outer_metrics_clip_1_to_5": True,
        "deployable_artifact_created": False,
        "original_artifact_loaded": False,
        "argentine_validation": False,
        "clinical_calibration": False,
        "runtime": {
            name: metadata.version(name)
            for name in ["numpy", "scipy", "scikit-learn", "joblib"]
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.source_zip)
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write("\n")
        print(
            "PASS: evaluacion OOF reproducida; no se creo ni reemplazo un modelo de entrega"
        )
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
