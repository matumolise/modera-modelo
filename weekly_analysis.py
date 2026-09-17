"""
Análisis semanal del comportamiento digital.

Utiliza el modelo PMU v1 para obtener una estimación continua
y conserva las métricas observables necesarias para
contextualizar el resultado.

IMPORTANTE:
- no produce un diagnóstico;
- no genera categorías clínicas bajo/medio/alto;
- no utiliza el score para bloquear el dispositivo;
- no inventa umbrales clínicos.
"""

from __future__ import annotations

from dataclasses import dataclass

from inference import (
    predict_pmu_severity,
)


@dataclass(frozen=True)
class WeeklyAnalysis:
    model_version: str
    predicted_severity: float
    prediction_within_expected_range: bool

    mean_daily_use_minutes: float
    mean_daily_session_count: float
    mean_daily_app_openings: float
    median_session_duration: float

    post_bedtime_use_ratio: float
    school_use_ratio: float


def analyze_week(
    feature_values: dict[str, float],
) -> WeeklyAnalysis:
    """
    Ejecuta la inferencia semanal utilizando las 11 features.

    Las validaciones estructurales y semánticas de las
    features son realizadas por inference.py.
    """

    prediction = predict_pmu_severity(
        feature_values
    )

    return WeeklyAnalysis(
        model_version=(
            prediction["model_version"]
        ),
        predicted_severity=(
            prediction["prediction"]
        ),
        prediction_within_expected_range=(
            prediction["within_expected_range"]
        ),
        mean_daily_use_minutes=float(
            feature_values[
                "mean_daily_use_minutes"
            ]
        ),
        mean_daily_session_count=float(
            feature_values[
                "mean_daily_session_count"
            ]
        ),
        mean_daily_app_openings=float(
            feature_values[
                "mean_daily_app_openings"
            ]
        ),
        median_session_duration=float(
            feature_values[
                "median_session_duration"
            ]
        ),
        post_bedtime_use_ratio=float(
            feature_values[
                "post_bedtime_use_ratio"
            ]
        ),
        school_use_ratio=float(
            feature_values[
                "school_use_ratio"
            ]
        ),
    )