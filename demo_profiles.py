from inference import predict_pmu_severity


# Ambos perfiles:
# - 9 años -> age_scaled = 0
# - mismo uso diario promedio: 175 min
#
# Se modifican otras dimensiones del comportamiento
# para observar cómo responde el modelo.

perfil_a = {
    "age_scaled": 0.0,
    "mean_daily_use_minutes": 175.0,
    "mean_daily_session_count": 18.0,
    "median_session_duration": 7.0,
    "mean_daily_app_openings": 38.0,
    "post_bedtime_use_ratio": 0.03,
    "school_use_ratio": 0.03,
    "games_share": 0.20,
    "social_share": 0.15,
    "entertainment_share": 0.25,
    "education_share": 0.20,
}

perfil_b = {
    "age_scaled": 0.0,
    "mean_daily_use_minutes": 175.0,
    "mean_daily_session_count": 34.0,
    "median_session_duration": 3.5,
    "mean_daily_app_openings": 75.0,
    "post_bedtime_use_ratio": 0.15,
    "school_use_ratio": 0.10,
    "games_share": 0.20,
    "social_share": 0.15,
    "entertainment_share": 0.25,
    "education_share": 0.20,
}


for nombre, perfil in [
    ("PERFIL A", perfil_a),
    ("PERFIL B", perfil_b),
]:
    resultado = predict_pmu_severity(perfil)

    print(f"\n{nombre}")
    print("-" * 30)
    print(
        f"Estimación: "
        f"{resultado['prediction']:.4f}"
    )
    print(
        f"Dentro del rango esperado: "
        f"{resultado['within_expected_range']}"
    )