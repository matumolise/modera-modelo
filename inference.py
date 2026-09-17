"""
Inferencia del modelo PMU v1.

Este módulo carga el artefacto entrenado y permite obtener
una predicción a partir de las 11 features semanales observables.

No entrena ni modifica el modelo.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# CARGA DEL MODELO
# ============================================================

def load_model_artifact(
    model_path: str = "models/pmu_linear_v1.joblib",
) -> dict:
    """Carga y valida la estructura mínima del artefacto."""

    path = Path(model_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en: {path}"
        )

    artifact = joblib.load(path)

    required_keys = {
        "model",
        "model_version",
        "model_type",
        "features",
        "n_features",
        "target",
        "target_range",
    }

    missing_keys = (
        required_keys - set(artifact.keys())
    )

    if missing_keys:
        raise ValueError(
            "El artefacto está incompleto. "
            f"Faltan: {sorted(missing_keys)}"
        )

    if (
        len(artifact["features"])
        != artifact["n_features"]
    ):
        raise ValueError(
            "El contrato de features del modelo "
            "es inconsistente."
        )

    return artifact


# ============================================================
# VALIDACIÓN DE ENTRADA
# ============================================================

def build_input_dataframe(
    feature_values: dict[str, float],
    expected_features: list[str],
) -> pd.DataFrame:
    """Valida un niño y construye X en el orden esperado."""

    received = set(feature_values.keys())
    expected = set(expected_features)

    missing = expected - received
    extra = received - expected

    if missing:
        raise ValueError(
            "Faltan features requeridas: "
            f"{sorted(missing)}"
        )

    if extra:
        raise ValueError(
            "Se recibieron features desconocidas: "
            f"{sorted(extra)}"
        )

    # El orden del diccionario recibido no importa.
    ordered_values = {
        feature: feature_values[feature]
        for feature in expected_features
    }

    X = pd.DataFrame(
        [ordered_values],
        columns=expected_features,
    )

    # Todas las entradas deben ser numéricas.
    try:
        numeric_values = X.to_numpy(
            dtype=float
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Todas las features deben ser numéricas."
        ) from exc

    if not np.isfinite(numeric_values).all():
        raise ValueError(
            "Las features no pueden contener "
            "NaN ni valores infinitos."
        )

    # ========================================================
    # VALIDACIÓN DE RANGOS SEMÁNTICOS
    # ========================================================

    # age_scaled corresponde a edades 6-12:
    # (age - 9) / 2 -> [-1.5, 1.5]
    age_scaled = float(
        X.loc[0, "age_scaled"]
    )

    if not -1.5 <= age_scaled <= 1.5:
        raise ValueError(
            "age_scaled debe estar entre -1.5 y 1.5."
        )

    # Métricas de uso: deben ser estrictamente positivas
    # en el esquema actual del MVP.
    positive_features = [
        "mean_daily_use_minutes",
        "mean_daily_session_count",
        "median_session_duration",
        "mean_daily_app_openings",
    ]

    for feature in positive_features:
        value = float(
            X.loc[0, feature]
        )

        if value <= 0:
            raise ValueError(
                f"{feature} debe ser mayor que 0."
            )

    # Ratios y shares siempre deben pertenecer a [0, 1].
    ratio_features = [
        "post_bedtime_use_ratio",
        "school_use_ratio",
        "games_share",
        "social_share",
        "entertainment_share",
        "education_share",
    ]

    for feature in ratio_features:
        value = float(
            X.loc[0, feature]
        )

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{feature} debe estar entre 0 y 1."
            )

    # Los cuatro shares expuestos no pueden superar 1
    # porque "other" ocupa el porcentaje restante.
    exposed_share_sum = sum(
        float(X.loc[0, feature])
        for feature in [
            "games_share",
            "social_share",
            "entertainment_share",
            "education_share",
        ]
    )

    if exposed_share_sum > 1.0 + 1e-10:
        raise ValueError(
            "La suma de los shares de categorías "
            "no puede superar 1."
        )

    return X


# ============================================================
# PREDICCIÓN
# ============================================================

def predict_pmu_severity(
    feature_values: dict[str, float],
    model_path: str = "models/pmu_linear_v1.joblib",
) -> dict:
    """
    Obtiene la estimación continua de severidad PMU sintética.

    La función no realiza clipping para no alterar
    silenciosamente la salida del modelo entrenado.
    """

    artifact = load_model_artifact(
        model_path=model_path
    )

    expected_features = list(
        artifact["features"]
    )

    X = build_input_dataframe(
        feature_values=feature_values,
        expected_features=expected_features,
    )

    prediction = float(
        artifact["model"].predict(X)[0]
    )

    target_min = float(
        artifact["target_range"][0]
    )

    target_max = float(
        artifact["target_range"][1]
    )

    within_expected_range = (
        target_min
        <= prediction
        <= target_max
    )

    return {
        "model_version": artifact["model_version"],
        "prediction": prediction,
        "target_min": target_min,
        "target_max": target_max,
        "within_expected_range": within_expected_range,
    }