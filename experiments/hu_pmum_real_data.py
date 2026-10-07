"""Exploración aislada de PMUM-SF con datos reales de PHI-CSU (Hungría).

Uso: python experiments/hu_pmum_real_data.py '/ruta/21802447.zip'
No guarda microdatos ni reemplaza el modelo de producción. Las dos variables
de pantalla son categorías ordinales, NO minutos observados por Android.
"""

import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FEATURES = ("age", "sex", "weekday_category", "weekend_category")


def names_from_input(script):
    match = re.search(r"names are(.*?);", script, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("SEM.inp no contiene la lista de variables")
    result = []
    for token in match.group(1).split():
        if "-" not in token:
            result.append(token)
            continue
        left, right = token.split("-", 1)
        a, b = re.fullmatch(r"(.+?)(\d+)", left), re.fullmatch(r"(.+?)(\d+)", right)
        if not a or not b or a.group(1) != b.group(1):
            raise ValueError(f"Rango de columnas desconocido: {token}")
        result.extend(f"{a.group(1)}{i}" for i in range(int(a.group(2)), int(b.group(2)) + 1))
    if len(result) != 122:
        raise ValueError(f"Esperábamos 122 variables, hay {len(result)}")
    return result


def parse_number(field):
    try:
        return float(field.strip())
    except ValueError:
        return float("nan")


def load_hungarian(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        names = names_from_input(archive.read("SEM.inp").decode("utf-8-sig"))
        lines = archive.read("SEM.dat").decode("utf-8-sig").splitlines()
    indices = {name: names.index(name) for name in (
        "ID", "filter", "NoChildren", "CHAge", "CHGender", "STIWeekday",
        "STIWeekend", "PMUMTotal", *(f"PMUM{i}" for i in range(1, 10)),
    )}
    rows, targets, one_child, ids = [], [], [], set()
    for line in lines:
        if len(line) != 122 * 8:
            raise ValueError("SEM.dat no conserva el formato fijo 122f8.2")

        def value(name):
            index = indices[name]
            return parse_number(line[8 * index:8 * (index + 1)])

        age = value("CHAge")
        if value("filter") != 1 or not 6 <= age <= 12:
            continue
        items = [value(f"PMUM{i}") for i in range(1, 10)]
        if not all(np.isfinite(x) and 1 <= x <= 5 and x.is_integer() for x in items):
            continue
        if value("PMUMTotal") != sum(items):
            raise ValueError("El puntaje PMUM no coincide con la suma de ítems")
        weekday, weekend, sex = value("STIWeekday"), value("STIWeekend"), value("CHGender")
        if weekday not in range(1, 6) or weekend not in range(1, 6):
            raise ValueError("Tiempo ordinal incompleto o fuera de rango")
        # En tres respuestas figura el código 4: conservarlo como categoría
        # sin adjudicarle una etiqueta cuyo significado no está confirmado.
        if np.isfinite(sex) and sex not in (1, 2, 4):
            raise ValueError("Código de sexo inesperado")
        sid = value("ID")
        if sid in ids:
            raise ValueError("ID de niño repetido")
        ids.add(sid)
        rows.append([age, str(int(sex)) if np.isfinite(sex) else "missing",
                     str(int(weekday)), str(int(weekend))])
        targets.append(sum(items) / 9)
        one_child.append(value("NoChildren") == 1)
    if len(rows) != 806:
        raise ValueError(f"Esperábamos 806 niños completos, hay {len(rows)}")
    return np.asarray(rows, dtype=object), np.asarray(targets), np.asarray(one_child)


def metrics(y_true, y_pred):
    return {
        "n": len(y_true),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
    }


def make_ridge(columns, alpha):
    transformers = []
    if 0 in columns:
        transformers.append(("age", make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler()), [columns.index(0)]))
    categoricals = [i for i, original_index in enumerate(columns) if original_index != 0]
    if categoricals:
        transformers.append(("categories", OneHotEncoder(handle_unknown="ignore"), categoricals))
    return make_pipeline(ColumnTransformer(transformers), Ridge(alpha=alpha))


def cross_fitted_diagnostics(x, y, one_child):
    """Todos los ajustes, incluido alpha, se eligen dentro del pliegue externo.

    Esta comprobación se añadió DESPUÉS de mirar el primer holdout; por ello
    sigue siendo exploratoria y no equivale a una validación independiente nueva.
    """
    outer = KFold(n_splits=5, shuffle=True, random_state=1027)
    preds = {name: np.full(len(y), np.nan) for name in
             ("mean", "age_sex", "screen_categories", "age_sex_weekend", "full")}
    feature_sets = {"age_sex": [0, 1], "screen_categories": [2, 3],
                    "age_sex_weekend": [0, 1, 3], "full": [0, 1, 2, 3]}
    for fold, (train, test) in enumerate(outer.split(x)):
        baseline = DummyRegressor(strategy="mean").fit(x[train], y[train])
        preds["mean"][test] = np.clip(baseline.predict(x[test]), 1, 5)
        inner = KFold(n_splits=4, shuffle=True, random_state=20261007 + fold)
        for name, columns in feature_sets.items():
            train_x, test_x = x[np.ix_(train, columns)], x[np.ix_(test, columns)]
            choices = [(float(-cross_val_score(make_ridge(columns, alpha), train_x,
                        y[train], cv=inner, scoring="neg_mean_absolute_error").mean()), alpha)
                       for alpha in (1, 10, 100)]
            alpha = min(choices)[1]
            fitted = make_ridge(columns, alpha).fit(train_x, y[train])
            preds[name][test] = np.clip(fitted.predict(test_x), 1, 5)
    groups = {"all": np.ones(len(y), dtype=bool), "one_child": one_child,
              "ages_6_to_9": x[:, 0].astype(float) < 10,
              "ages_10_to_12": x[:, 0].astype(float) >= 10}
    summaries = {group: {name: metrics(y[mask], values[mask])
                         for name, values in preds.items()}
                 for group, mask in groups.items()}
    # Intervalo descriptivo por remuestreo de niños sobre las predicciones
    # cruzadas fijas. No recoge incertidumbre de volver a entrenar el modelo.
    rng = np.random.default_rng(17)
    gain = np.abs(y - preds["mean"]) - np.abs(y - preds["full"])
    sampled = rng.choice(gain, size=(2000, len(gain)), replace=True).mean(axis=1)
    return {"nested_cv": summaries,
            "mae_gain_full_vs_mean": round(float(gain.mean()), 4),
            "paired_bootstrap_gain_interval_95_descriptive":
                [round(float(v), 4) for v in np.quantile(sampled, [0.025, 0.975])]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_hu", type=Path)
    args = parser.parse_args()
    x, y, one_child = load_hungarian(args.zip_hu)
    indices = np.arange(len(y))
    train, test = train_test_split(indices, test_size=0.2, random_state=20261007)
    # Sexo y tiempo ingresan como categorías; edad sigue siendo una magnitud numérica.
    preprocessor = ColumnTransformer([
        ("age", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), [0]),
        ("categories", OneHotEncoder(handle_unknown="ignore"), [1, 2, 3]),
    ])
    candidates = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "ridge_1": make_pipeline(preprocessor, Ridge(alpha=1)),
        "ridge_10": make_pipeline(preprocessor, Ridge(alpha=10)),
        "ridge_100": make_pipeline(preprocessor, Ridge(alpha=100)),
    }
    folds = KFold(n_splits=5, shuffle=True, random_state=20261007)
    cv = {name: round(float(-cross_val_score(model, x[train], y[train], cv=folds,
                                            scoring="neg_mean_absolute_error").mean()), 4)
          for name, model in candidates.items()}
    selected = min((name for name in candidates if name != "mean_baseline"), key=cv.get)
    fitted = {}
    for name in ("mean_baseline", selected):
        model = candidates[name].fit(x[train], y[train])
        predicted = np.clip(model.predict(x[test]), 1, 5)
        fitted[name] = {
            "all_test": metrics(y[test], predicted),
            "one_child_test": metrics(y[test][one_child[test]], predicted[one_child[test]])
            if sum(one_child[test]) >= 2 else None,
        }
    sex_binary = x[:, 1] != "4"
    diagnostics = cross_fitted_diagnostics(x, y, one_child)
    # SEM.inp excluye CHGender > 2: una sensibilidad permite comprobar si
    # preservar el código 4 (sin etiquetar) altera materialmente el resultado.
    binary_only = cross_fitted_diagnostics(x[sex_binary], y[sex_binary],
                                           one_child[sex_binary])
    print(json.dumps({"dataset": "PHI-CSU SEM.dat", "target": "PMUMTotal / 9",
                      "features": FEATURES, "n_total": len(y), "n_train": len(train),
                      "n_test": len(test), "n_one_child_test": int(sum(one_child[test])),
                      "cv_train_MAE": cv, "selected": selected, "holdout": fitted,
                      "scope": "Exploratory Hungarian parent-report; no Argentine or Android validation",
                      "additional_diagnostics": diagnostics,
                      "sensitivity_exclude_three_sex_code_4": {
                          "n": int(sum(sex_binary)),
                          "nested_cv_all_mean": binary_only["nested_cv"]["all"]["mean"],
                          "nested_cv_all_full": binary_only["nested_cv"]["all"]["full"],
                          "nested_cv_one_child_full":
                              binary_only["nested_cv"]["one_child"]["full"]}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
