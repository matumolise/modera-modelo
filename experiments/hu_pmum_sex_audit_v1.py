"""Diagnóstico exploratorio agregado de la entrada sexo en PHI-CSU.

Uso: python experiments/hu_pmum_sex_audit_v1.py ZIP_HU
No imprime ni guarda filas individuales.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold, cross_val_score

from hu_pmum_candidate_v1 import EXPECTED_SHA256, sha256
from hu_pmum_real_data import load_hungarian, make_ridge


def cross_fitted(x, y, columns):
    predictions = np.empty(len(y))
    outer = KFold(n_splits=5, shuffle=True, random_state=1027)
    for fold, (train, test) in enumerate(outer.split(x)):
        inner = KFold(n_splits=4, shuffle=True, random_state=20261007 + fold)
        alpha = min((float(-cross_val_score(make_ridge(columns, value),
                      x[np.ix_(train, columns)], y[train], cv=inner,
                      scoring="neg_mean_absolute_error").mean()), value)
                     for value in (1, 10, 100))[1]
        model = make_ridge(columns, alpha).fit(x[np.ix_(train, columns)], y[train])
        predictions[test] = np.clip(model.predict(x[np.ix_(test, columns)]), 1, 5)
    return predictions


def group_metrics(y, prediction, selected):
    return {"n": int(selected.sum()),
            "MAE": round(float(np.abs(y[selected] - prediction[selected]).mean()), 4),
            "mean_signed_error_pred_minus_observed":
                round(float((prediction[selected] - y[selected]).mean()), 4),
            "observed_mean": round(float(y[selected].mean()), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_hu")
    args = parser.parse_args()
    if sha256(Path(args.zip_hu)) != EXPECTED_SHA256:
        raise ValueError("ZIP diferente del auditado")
    x, y, one_child = load_hungarian(args.zip_hu)
    allowed = x[:, 1] != "4"
    x, y, one_child = x[allowed], y[allowed], one_child[allowed]
    groups = {"all": np.ones(len(y), dtype=bool), "sex_code_1": x[:, 1] == "1",
              "sex_code_2": x[:, 1] == "2", "one_child": one_child,
              "more_than_one_child": ~one_child}
    results = {}
    for label, features in (("four", [0, 1, 2, 3]),
                            ("without_sex", [0, 2, 3])):
        pred = cross_fitted(x, y, features)
        results[label] = {name: group_metrics(y, pred, mask) for name, mask in groups.items()}
    print(json.dumps({"purpose": "exploratory diagnostic, not Argentine validation",
                      "source_sha256": EXPECTED_SHA256, "results": results},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
