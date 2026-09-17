"""
Generación del target sintético del Dataset A.

El target se genera exclusivamente a partir de variables latentes
de nivel niño y ruido independiente.

Las features observables NO participan en la construcción del target.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def sigmoid(values: np.ndarray) -> np.ndarray:
    """Transforma valores reales al intervalo abierto (0, 1)."""

    return 1.0 / (1.0 + np.exp(-values))


# ============================================================
# GENERACIÓN DEL TARGET
# ============================================================

def generate_synthetic_target(
    population: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Genera una severidad sintética continua entre 1 y 5 por niño."""

    # S y U son variables latentes internas de nivel niño.
    child_latents = (
        population[
            [
                "child_id",
                "S",
                "U",
            ]
        ]
        .copy()
        .sort_values("child_id")
        .reset_index(drop=True)
    )

    # Ruido independiente específico del target.
    target_noise = rng.normal(
        loc=0.0,
        scale=config.TARGET_NOISE_SIGMA,
        size=len(child_latents),
    )

    # Y* = beta_S*S + beta_U*U + epsilon
    y_star = (
        config.TARGET_BETA_S
        * child_latents["S"].to_numpy(dtype=float)
        + config.TARGET_BETA_U
        * child_latents["U"].to_numpy(dtype=float)
        + target_noise
    )

    # Transformación monótona desde R al intervalo abierto
    # (TARGET_MIN, TARGET_MAX).
    target = (
        config.TARGET_MIN
        + (
            config.TARGET_MAX
            - config.TARGET_MIN
        )
        * sigmoid(y_star)
    )

    return pd.DataFrame(
        {
            "child_id": (
                child_latents["child_id"]
                .to_numpy(dtype=int)
            ),
            "y_star": y_star,
            "target_noise": target_noise,
            "synthetic_pmu_severity": target,
        }
    )


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_synthetic_target(
    target_data: pd.DataFrame,
    population: pd.DataFrame,
) -> None:
    """Valida estructura, rango y relaciones del target sintético."""

    print("\nVALIDACIÓN DEL TARGET SINTÉTICO\n")

    # Debe existir exactamente un target por niño.
    assert len(target_data) == len(population)
    assert target_data["child_id"].is_unique

    # No debe haber valores faltantes o infinitos.
    assert not target_data.isna().any().any()

    numeric_values = target_data[
        [
            "y_star",
            "target_noise",
            "synthetic_pmu_severity",
        ]
    ].to_numpy(dtype=float)

    assert np.isfinite(numeric_values).all()

    # La sigmoid genera valores estrictamente dentro del rango.
    assert (
        target_data["synthetic_pmu_severity"]
        > config.TARGET_MIN
    ).all()

    assert (
        target_data["synthetic_pmu_severity"]
        < config.TARGET_MAX
    ).all()

    print("Una fila por niño: OK")
    print("Sin NaN ni infinitos: OK")
    print(
        f"Target dentro de "
        f"({config.TARGET_MIN}, {config.TARGET_MAX}): OK"
    )

    print("\nResumen del target:")

    print(
        target_data["synthetic_pmu_severity"]
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

    # --------------------------------------------------------
    # DIAGNÓSTICO DEL DGM
    # --------------------------------------------------------

    # Las latentes se utilizan únicamente para auditar el
    # mecanismo generador. Nunca serán features del modelo.
    diagnostic = target_data.merge(
        population[
            [
                "child_id",
                "S",
                "B",
                "F",
                "U",
            ]
        ],
        on="child_id",
        validate="one_to_one",
    )

    print("\nCorrelaciones latentes con Y*:")

    print(
        diagnostic[
            [
                "y_star",
                "S",
                "B",
                "F",
                "U",
            ]
        ]
        .corr()["y_star"]
        .round(3)
    )

    print("\nCorrelaciones latentes con target 1-5:")

    print(
        diagnostic[
            [
                "synthetic_pmu_severity",
                "S",
                "B",
                "F",
                "U",
            ]
        ]
        .corr()["synthetic_pmu_severity"]
        .round(3)
    )