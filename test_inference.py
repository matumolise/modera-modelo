from inference import predict_pmu_severity


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

result = predict_pmu_severity(
    example_child
)

print("\nPRUEBA DE INFERENCIA\n")

print(
    f"Versión del modelo: "
    f"{result['model_version']}"
)

print(
    f"Predicción: "
    f"{result['prediction']:.4f}"
)

print(
    f"Rango esperado: "
    f"{result['target_min']} - "
    f"{result['target_max']}"
)

print(
    f"Dentro del rango: "
    f"{result['within_expected_range']}"
)

print("\nVALIDACIÓN DE ENTRADAS INVÁLIDAS\n")


# ============================================================
# TEST 1: FEATURE FALTANTE
# ============================================================

missing_feature_child = example_child.copy()

missing_feature_child.pop(
    "mean_daily_use_minutes"
)

try:
    predict_pmu_severity(
        missing_feature_child
    )

    print(
        "Feature faltante: ERROR "
        "(la entrada fue aceptada)"
    )

except ValueError:
    print(
        "Feature faltante: OK"
    )


# ============================================================
# TEST 2: FEATURE DESCONOCIDA
# ============================================================

extra_feature_child = example_child.copy()

extra_feature_child[
    "unknown_feature"
] = 123.0

try:
    predict_pmu_severity(
        extra_feature_child
    )

    print(
        "Feature desconocida: ERROR "
        "(la entrada fue aceptada)"
    )

except ValueError:
    print(
        "Feature desconocida: OK"
    )


# ============================================================
# TEST 3: NaN
# ============================================================

nan_child = example_child.copy()

nan_child[
    "mean_daily_use_minutes"
] = float("nan")

try:
    predict_pmu_severity(
        nan_child
    )

    print(
        "NaN: ERROR "
        "(la entrada fue aceptada)"
    )

except ValueError:
    print(
        "NaN: OK"
    )


# ============================================================
# TEST 4: INFINITO
# ============================================================

infinite_child = example_child.copy()

infinite_child[
    "mean_daily_use_minutes"
] = float("inf")

try:
    predict_pmu_severity(
        infinite_child
    )

    print(
        "Infinito: ERROR "
        "(la entrada fue aceptada)"
    )

except ValueError:
    print(
        "Infinito: OK"
    )


# ============================================================
# TEST 5: ORDEN DIFERENTE
# ============================================================

reversed_child = dict(
    reversed(
        list(
            example_child.items()
        )
    )
)

reordered_result = predict_pmu_severity(
    reversed_child
)

same_prediction = abs(
    reordered_result["prediction"]
    - result["prediction"]
) < 1e-12

print(
    "Orden diferente: "
    + (
        "OK"
        if same_prediction
        else "ERROR"
    )
)

# Ratio imposible.
invalid_ratio_child = example_child.copy()
invalid_ratio_child["school_use_ratio"] = 1.5

try:
    predict_pmu_severity(invalid_ratio_child)
    print("Ratio fuera de rango: ERROR")
except ValueError:
    print("Ratio fuera de rango: OK")


# Métrica negativa.
negative_child = example_child.copy()
negative_child["mean_daily_use_minutes"] = -10.0

try:
    predict_pmu_severity(negative_child)
    print("Métrica negativa: ERROR")
except ValueError:
    print("Métrica negativa: OK")