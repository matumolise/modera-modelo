from weekly_analysis import (
    analyze_week,
)


example_child = {
    "age_scaled": 0.0,
    "mean_daily_use_minutes": 175.0,
    "mean_daily_session_count": 25.0,
    "median_session_duration": 4.5,
    "mean_daily_app_openings": 55.0,
    "post_bedtime_use_ratio": 0.11,
    "school_use_ratio": 0.06,
    "games_share": 0.20,
    "social_share": 0.20,
    "entertainment_share": 0.20,
    "education_share": 0.20,
}

analysis = analyze_week(
    example_child
)

print("\nANÁLISIS SEMANAL DEL NIÑO\n")

print(
    f"Modelo: {analysis.model_version}"
)

print(
    f"Estimación continua: "
    f"{analysis.predicted_severity:.4f} / 5"
)

print(
    f"Predicción dentro del rango esperado: "
    f"{analysis.prediction_within_expected_range}"
)

print("\nMétricas observadas:")

print(
    f"- Uso diario medio: "
    f"{analysis.mean_daily_use_minutes:.2f} min"
)

print(
    f"- Sesiones diarias medias: "
    f"{analysis.mean_daily_session_count:.2f}"
)

print(
    f"- Aperturas diarias medias: "
    f"{analysis.mean_daily_app_openings:.2f}"
)

print(
    f"- Duración mediana de sesión: "
    f"{analysis.median_session_duration:.2f} min"
)

print(
    f"- Uso post-bedtime: "
    f"{analysis.post_bedtime_use_ratio:.2%}"
)

print(
    f"- Uso escolar: "
    f"{analysis.school_use_ratio:.2%}"
)