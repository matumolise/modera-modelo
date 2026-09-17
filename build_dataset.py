"""
Construcción y auditoría del Dataset A final para ML.

Este módulo combina las features observables con el target sintético
y verifica explícitamente que no exista data leakage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ============================================================
# CONSTRUCCIÓN DEL DATASET A
# ============================================================

def build_dataset_a(
    features: pd.DataFrame,
    target_data: pd.DataFrame,
) -> pd.DataFrame:
    """Combina features observables y target sintético por child_id."""

    target_for_ml = target_data[
        [
            "child_id",
            "synthetic_pmu_severity",
        ]
    ].copy()

    dataset = features.merge(
        target_for_ml,
        on="child_id",
        how="inner",
        validate="one_to_one",
    )

    expected_columns = [
        "child_id",
        *config.DATASET_A_FEATURES,
        "synthetic_pmu_severity",
    ]

    return dataset[expected_columns]


# ============================================================
# AUDITORÍA ANTI-LEAKAGE
# ============================================================

def validate_dataset_a(
    dataset: pd.DataFrame,
    expected_children: int,
) -> None:
    """Verifica estructura, integridad y ausencia de leakage."""

    print("\nVALIDACIÓN DEL DATASET A\n")

    expected_columns = [
        "child_id",
        *config.DATASET_A_FEATURES,
        "synthetic_pmu_severity",
    ]

    # --------------------------------------------------------
    # ESTRUCTURA
    # --------------------------------------------------------

    assert len(dataset) == expected_children
    assert dataset["child_id"].is_unique

    assert list(dataset.columns) == expected_columns

    assert not dataset.isna().any().any()

    numeric_values = dataset[
        [
            *config.DATASET_A_FEATURES,
            "synthetic_pmu_severity",
        ]
    ].to_numpy(dtype=float)

    assert np.isfinite(numeric_values).all()

    # --------------------------------------------------------
    # ANTI-LEAKAGE
    # --------------------------------------------------------

    # child_id puede permanecer en el dataset maestro únicamente
    # como identificador, pero nunca podrá entrar en X.
    forbidden_dataset_columns = (
        set(config.FORBIDDEN_MODEL_FEATURES)
        - {"child_id"}
    )

    forbidden_present = (
        forbidden_dataset_columns
        & set(dataset.columns)
    )

    assert len(forbidden_present) == 0, (
        "Se detectaron variables internas prohibidas en Dataset A: "
        f"{sorted(forbidden_present)}"
    )

    # El target tampoco puede formar parte de la whitelist X.
    assert (
        "synthetic_pmu_severity"
        not in config.DATASET_A_FEATURES
    )

    # child_id se conserva solo como identificador.
    assert "child_id" not in config.DATASET_A_FEATURES

    print("Cantidad de niños correcta: OK")
    print("Una fila por niño: OK")
    print("Columnas exactas: OK")
    print("Sin NaN ni infinitos: OK")
    print("Variables prohibidas ausentes: OK")
    print("Target fuera de X: OK")
    print("child_id fuera de X: OK")

    print("\nDimensiones del Dataset A:")
    print(
        f"{dataset.shape[0]} filas x "
        f"{dataset.shape[1]} columnas"
    )

    print("\nColumnas del Dataset A:")
    print(dataset.columns.tolist())


# ============================================================
# SEPARACIÓN X / y
# ============================================================

def split_x_y(
    dataset: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separa predictores observables y target."""

    X = dataset[
        config.DATASET_A_FEATURES
    ].copy()

    y = dataset[
        "synthetic_pmu_severity"
    ].copy()

    return X, y


def validate_x_y(
    X: pd.DataFrame,
    y: pd.Series,
    expected_children: int,
) -> None:
    """Verifica la matriz X y el vector y antes del modelado."""

    print("\nVALIDACIÓN FINAL DE X / y\n")

    assert X.shape == (
        expected_children,
        len(config.DATASET_A_FEATURES),
    )

    assert len(y) == expected_children

    assert list(X.columns) == config.DATASET_A_FEATURES

    assert not X.isna().any().any()
    assert not y.isna().any()

    # Defensa explícita: ninguna variable interna puede entrar a X.
    forbidden_in_x = (
        set(config.FORBIDDEN_MODEL_FEATURES)
        & set(X.columns)
    )

    assert len(forbidden_in_x) == 0

    print(
        f"X: {X.shape[0]} filas x "
        f"{X.shape[1]} features"
    )
    print(f"y: {len(y)} valores")
    print("Whitelist de X respetada: OK")
    print("Sin variables internas en X: OK")