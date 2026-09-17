from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import config


# ============================================================
# CARGA DEL MODELO
# ============================================================

artifact = joblib.load(
    "models/pmu_linear_v1.joblib"
)

model = artifact["model"]
features = artifact["features"]


# ============================================================
# BUSCAR AUTOMÁTICAMENTE DATASET CON LAS 11 FEATURES
# ============================================================

candidate_files = list(
    Path("data/final").glob("*.csv")
)

dataset = None
dataset_path = None

for path in candidate_files:
    try:
        df = pd.read_csv(path)

        if set(features).issubset(df.columns):
            dataset = df.copy()
            dataset_path = path
            break

    except Exception:
        pass


if dataset is None:
    raise FileNotFoundError(
        "No encontré en data/final un CSV "
        "que contenga las 11 features."
    )

print(
    f"\nDataset encontrado: {dataset_path}"
)

print(
    f"Cantidad de perfiles: {len(dataset)}"
)


# ============================================================
# PREDICCIONES
# ============================================================

X = dataset[features].copy()

dataset["prediction"] = model.predict(X)


print("\n========================================")
print("1. DISTRIBUCIÓN DE PREDICCIONES")
print("========================================\n")

print(
    dataset["prediction"]
    .describe(
        percentiles=[
            0.05,
            0.25,
            0.50,
            0.75,
            0.95,
        ]
    )
    .round(4)
)


# ============================================================
# COEFICIENTES ESTANDARIZADOS
# ============================================================

feature_std = X.std(ddof=1)

standardized_effect = (
    pd.Series(
        model.coef_,
        index=features,
    )
    * feature_std
)

coef_table = pd.DataFrame(
    {
        "feature": features,
        "coef_raw": model.coef_,
        "std_dataset": feature_std.values,
        "effect_1_std": standardized_effect.values,
    }
)

coef_table["abs_effect_1_std"] = (
    coef_table["effect_1_std"].abs()
)

coef_table = coef_table.sort_values(
    "abs_effect_1_std",
    ascending=False,
)


print("\n========================================")
print("2. EFECTO DE +1 DESVÍO ESTÁNDAR")
print("========================================\n")

print(
    coef_table[
        [
            "feature",
            "effect_1_std",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# ============================================================
# CAMBIO P25 -> P75, UNA FEATURE POR VEZ
# ============================================================

baseline = X.median()

sensitivity_rows = []

for feature in features:

    low = float(
        X[feature].quantile(0.25)
    )

    high = float(
        X[feature].quantile(0.75)
    )

    profile_low = baseline.copy()
    profile_high = baseline.copy()

    profile_low[feature] = low
    profile_high[feature] = high

    pred_low = float(
        model.predict(
            pd.DataFrame(
                [profile_low],
                columns=features,
            )
        )[0]
    )

    pred_high = float(
        model.predict(
            pd.DataFrame(
                [profile_high],
                columns=features,
            )
        )[0]
    )

    sensitivity_rows.append(
        {
            "feature": feature,
            "p25": low,
            "p75": high,
            "prediction_p25": pred_low,
            "prediction_p75": pred_high,
            "delta": pred_high - pred_low,
        }
    )


sensitivity = pd.DataFrame(
    sensitivity_rows
)

sensitivity["abs_delta"] = (
    sensitivity["delta"].abs()
)

sensitivity = sensitivity.sort_values(
    "abs_delta",
    ascending=False,
)


print("\n========================================")
print("3. SENSIBILIDAD P25 -> P75")
print("   UNA FEATURE POR VEZ")
print("========================================\n")

print(
    sensitivity[
        [
            "feature",
            "p25",
            "p75",
            "delta",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# ============================================================
# BUSCAR DOS PERFILES REALES:
# MISMA EDAD + TIEMPO MUY SIMILAR
# ============================================================

# Evitamos extremos del dataset para obtener
# ejemplos visualmente defendibles.
filtered = dataset.copy()

for feature in features:

    low = dataset[feature].quantile(0.05)
    high = dataset[feature].quantile(0.95)

    filtered = filtered[
        filtered[feature].between(
            low,
            high,
        )
    ]


best_pair = None
best_prediction_difference = -np.inf

rows = filtered.reset_index(drop=True)


for i in range(len(rows)):

    a = rows.iloc[i]

    # Mismo age_scaled.
    candidates = rows[
        np.isclose(
            rows["age_scaled"],
            a["age_scaled"],
        )
    ]

    # Máximo 3 minutos de diferencia
    # en uso diario promedio.
    candidates = candidates[
        (
            candidates[
                "mean_daily_use_minutes"
            ]
            - a[
                "mean_daily_use_minutes"
            ]
        ).abs() <= 3.0
    ]

    for _, b in candidates.iterrows():

        if a.name == b.name:
            continue

        difference = abs(
            a["prediction"]
            - b["prediction"]
        )

        if (
            difference
            > best_prediction_difference
        ):
            best_prediction_difference = difference
            best_pair = (
                a.copy(),
                b.copy(),
            )


print("\n========================================")
print("4. MEJOR PAR ENCONTRADO")
print("MISMA EDAD Y USO ±3 MIN")
print("========================================\n")


if best_pair is None:
    print(
        "No se encontró un par adecuado."
    )

else:

    a, b = best_pair

    comparison_features = [
        "age_scaled",
        "mean_daily_use_minutes",
        "mean_daily_session_count",
        "median_session_duration",
        "mean_daily_app_openings",
        "post_bedtime_use_ratio",
        "school_use_ratio",
        "games_share",
        "social_share",
        "entertainment_share",
        "education_share",
        "prediction",
    ]

    comparison = pd.DataFrame(
        {
            "Perfil_A": a[
                comparison_features
            ],
            "Perfil_B": b[
                comparison_features
            ],
        }
    )

    print(
        comparison
        .round(4)
        .to_string()
    )

    print(
        "\nDiferencia de predicción: "
        f"{best_prediction_difference:.4f}"
    )


# ============================================================
# VARIACIÓN DE PREDICCIÓN CON TIEMPO SIMILAR
# ============================================================

print("\n========================================")
print("5. MISMO TIEMPO, DISTINTA PREDICCIÓN")
print("========================================\n")

# Bandas de 10 minutos.
dataset["use_band"] = (
    (
        dataset[
            "mean_daily_use_minutes"
        ]
        / 10
    )
    .round()
    * 10
)

band_summary = (
    dataset
    .groupby("use_band")
    .agg(
        n=("prediction", "size"),
        mean_prediction=(
            "prediction",
            "mean",
        ),
        min_prediction=(
            "prediction",
            "min",
        ),
        max_prediction=(
            "prediction",
            "max",
        ),
        std_prediction=(
            "prediction",
            "std",
        ),
    )
)

band_summary["prediction_range"] = (
    band_summary["max_prediction"]
    - band_summary["min_prediction"]
)

# Solo bandas con suficientes casos.
band_summary = band_summary[
    band_summary["n"] >= 15
]

band_summary = band_summary.sort_values(
    "prediction_range",
    ascending=False,
)


print(
    band_summary
    .head(15)
    .round(4)
    .to_string()
)