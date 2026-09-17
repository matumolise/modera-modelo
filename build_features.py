"""
Construcción de features semanales del Dataset A.

Este módulo transforma el comportamiento sintético observable
en las variables que podrá recibir el modelo de ML.

No genera nuevas variables conductuales ni utiliza variables
latentes como predictores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ============================================================
# CONSTRUCCIÓN DE FEATURES
# ============================================================

def build_weekly_features(
    daily_behavior: pd.DataFrame,
    scheduled_sessions: pd.DataFrame,
    app_episodes: pd.DataFrame,
) -> pd.DataFrame:
    """Construye una fila semanal de features por niño."""

    # --------------------------------------------------------
    # PERFIL OBSERVABLE DEL NIÑO
    # --------------------------------------------------------

    child_profile = (
        daily_behavior[
            [
                "child_id",
                "age_scaled",
            ]
        ]
        .drop_duplicates(subset=["child_id"])
        .copy()
    )

    # --------------------------------------------------------
    # MÉTRICAS DIARIAS
    # --------------------------------------------------------

    # Cantidad de entradas a foreground por niño-día.
    # En Base v1 cada episodio representa una entrada operacional
    # de una app a foreground.
    daily_openings = (
        app_episodes
        .groupby(
            [
                "child_id",
                "day_index",
            ]
        )
        .size()
        .rename("daily_app_openings")
        .reset_index()
    )

    daily_metrics = daily_behavior[
        [
            "child_id",
            "day_index",
            "daily_use_minutes",
            "daily_session_count",
        ]
    ].merge(
        daily_openings,
        on=["child_id", "day_index"],
        how="left",
        validate="one_to_one",
    )

    # Base v1 genera al menos una sesión y un episodio por día.
    # El fillna mantiene robusta la función ante escenarios futuros.
    daily_metrics["daily_app_openings"] = (
        daily_metrics["daily_app_openings"]
        .fillna(0)
    )

    weekly_daily_metrics = (
        daily_metrics
        .groupby("child_id")
        .agg(
            mean_daily_use_minutes=(
                "daily_use_minutes",
                "mean",
            ),
            mean_daily_session_count=(
                "daily_session_count",
                "mean",
            ),
            mean_daily_app_openings=(
                "daily_app_openings",
                "mean",
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # DURACIÓN MEDIANA DE SESIÓN
    # --------------------------------------------------------

    median_session_duration = (
        scheduled_sessions
        .groupby("child_id")
        ["session_duration_minutes"]
        .median()
        .rename("median_session_duration")
        .reset_index()
    )

    # --------------------------------------------------------
    # RATIOS CONTEXTUALES SEMANALES
    # --------------------------------------------------------

    contextual_minutes = (
        scheduled_sessions
        .groupby("child_id")
        .agg(
            school_use_minutes=(
                "school_use_minutes",
                "sum",
            ),
            post_bedtime_use_minutes=(
                "post_bedtime_use_minutes",
                "sum",
            ),
        )
        .reset_index()
    )

    weekly_total_use = (
        daily_behavior
        .groupby("child_id")
        ["daily_use_minutes"]
        .sum()
        .rename("weekly_total_use_minutes")
        .reset_index()
    )

    contextual_ratios = contextual_minutes.merge(
        weekly_total_use,
        on="child_id",
        validate="one_to_one",
    )

    # Ratio de sumas semanales, no promedio de ratios diarios.
    contextual_ratios["school_use_ratio"] = (
        contextual_ratios["school_use_minutes"]
        / contextual_ratios["weekly_total_use_minutes"]
    )

    contextual_ratios["post_bedtime_use_ratio"] = (
        contextual_ratios["post_bedtime_use_minutes"]
        / contextual_ratios["weekly_total_use_minutes"]
    )

    contextual_ratios = contextual_ratios[
        [
            "child_id",
            "school_use_ratio",
            "post_bedtime_use_ratio",
        ]
    ]

    # --------------------------------------------------------
    # SHARES DE CATEGORÍAS
    # --------------------------------------------------------

    category_minutes = (
        app_episodes
        .pivot_table(
            index="child_id",
            columns="app_category",
            values="episode_duration_minutes",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(
            columns=config.APP_CATEGORIES,
            fill_value=0.0,
        )
    )

    # El denominador contiene TODAS las categorías,
    # incluida "other".
    total_app_minutes = category_minutes.sum(axis=1)

    category_shares = (
        category_minutes
        .div(total_app_minutes, axis=0)
    )

    category_features = pd.DataFrame(
        {
            "child_id": category_shares.index,
            "games_share": category_shares["games"],
            "social_share": category_shares["social"],
            "entertainment_share": (
                category_shares["entertainment"]
            ),
            "education_share": (
                category_shares["education"]
            ),
        }
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # TABLA FINAL DE FEATURES
    # --------------------------------------------------------

    features = (
        child_profile
        .merge(
            weekly_daily_metrics,
            on="child_id",
            validate="one_to_one",
        )
        .merge(
            median_session_duration,
            on="child_id",
            validate="one_to_one",
        )
        .merge(
            contextual_ratios,
            on="child_id",
            validate="one_to_one",
        )
        .merge(
            category_features,
            on="child_id",
            validate="one_to_one",
        )
    )

    # Orden explícito para evitar cambios accidentales.
    return features[
        [
            "child_id",
            *config.DATASET_A_FEATURES,
        ]
    ]


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_weekly_features(
    features: pd.DataFrame,
    expected_children: int,
) -> None:
    """Verifica estructura, rangos y ausencia de valores inválidos."""

    print("\nVALIDACIÓN DE FEATURES SEMANALES\n")

    # Una única fila por niño.
    assert len(features) == expected_children
    assert features["child_id"].is_unique

    # Deben existir exactamente las features preespecificadas.
    assert list(
        features.columns
    ) == [
        "child_id",
        *config.DATASET_A_FEATURES,
    ]

    # No debe faltar ningún valor.
    assert not features.isna().any().any()

    # Todas las features deben ser numéricas y finitas.
    feature_values = features[
        config.DATASET_A_FEATURES
    ].to_numpy(dtype=float)

    assert np.isfinite(feature_values).all()

    # Métricas estrictamente positivas en Base v1.
    positive_features = [
        "mean_daily_use_minutes",
        "mean_daily_session_count",
        "median_session_duration",
        "mean_daily_app_openings",
    ]

    assert (
        features[positive_features] > 0
    ).all().all()

    # Ratios y shares deben estar entre 0 y 1.
    ratio_features = [
        "post_bedtime_use_ratio",
        "school_use_ratio",
        "games_share",
        "social_share",
        "entertainment_share",
        "education_share",
    ]

    assert (
        features[ratio_features]
        .ge(0)
        .all()
        .all()
    )

    assert (
        features[ratio_features]
        .le(1)
        .all()
        .all()
    )

    # Los cuatro shares expuestos no pueden sumar más de 1,
    # ya que "other" permanece en el denominador.
    exposed_share_sum = features[
        [
            "games_share",
            "social_share",
            "entertainment_share",
            "education_share",
        ]
    ].sum(axis=1)

    assert (
        exposed_share_sum <= 1.0 + 1e-10
    ).all()

    print("Una fila por niño: OK")
    print("Whitelist de features: OK")
    print("Sin NaN ni infinitos: OK")
    print("Métricas positivas: OK")
    print("Ratios y shares en [0, 1]: OK")
    print("Shares expuestos <= 1: OK")

    print("\nResumen de features:")

    print(
        features[
            config.DATASET_A_FEATURES
        ]
        .describe()
        .T[
            [
                "mean",
                "std",
                "min",
                "50%",
                "max",
            ]
        ]
        .round(4)
    )


# ============================================================
# DIAGNÓSTICOS ESTRUCTURALES
# ============================================================

def diagnose_feature_relationships(
    features: pd.DataFrame,
) -> None:
    """Diagnostica relaciones estructurales entre features candidatas."""

    print("\nDIAGNÓSTICO DE RELACIONES ENTRE FEATURES\n")

    # Redundancia preespecificada para revisar:
    # tiempo total, sesiones y entradas a foreground.
    redundancy_features = [
        "mean_daily_use_minutes",
        "mean_daily_session_count",
        "mean_daily_app_openings",
    ]

    print("Correlaciones T - N - openings:")

    print(
        features[
            redundancy_features
        ]
        .corr()
        .round(3)
    )

    print("\nCorrelaciones completas de las 11 features:")

    print(
        features[
            config.DATASET_A_FEATURES
        ]
        .corr()
        .round(3)
    )

def diagnose_app_opening_redundancy(
    features: pd.DataFrame,
    daily_behavior: pd.DataFrame,
) -> None:
    """Evalúa si openings aporta información adicional a T y N."""

    print("\nDIAGNÓSTICO DE REDUNDANCIA DE APP OPENINGS\n")

    # Recupera F únicamente para diagnóstico del DGM.
    # F NO será utilizada como feature del modelo.
    child_fragmentation = (
        daily_behavior[
            [
                "child_id",
                "F",
            ]
        ]
        .drop_duplicates(subset=["child_id"])
    )

    diagnostic = features.merge(
        child_fragmentation,
        on="child_id",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # REGRESIÓN OPENINGS ~ T + N
    # --------------------------------------------------------

    y = diagnostic[
        "mean_daily_app_openings"
    ].to_numpy(dtype=float)

    X = diagnostic[
        [
            "mean_daily_use_minutes",
            "mean_daily_session_count",
        ]
    ].to_numpy(dtype=float)

    # Agrega intercepto.
    X_design = np.column_stack(
        [
            np.ones(len(X)),
            X,
        ]
    )

    coefficients, _, _, _ = np.linalg.lstsq(
        X_design,
        y,
        rcond=None,
    )

    predicted = X_design @ coefficients
    residuals = y - predicted

    # R²: proporción de variabilidad de openings
    # explicada conjuntamente por T y N.
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum(
        (y - y.mean()) ** 2
    )

    r_squared = 1.0 - (ss_res / ss_tot)

    diagnostic["openings_residual"] = residuals

    print(
        "R² de openings explicado por T + N: "
        f"{r_squared:.4f}"
    )

    print(
        "Desvío estándar original de openings: "
        f"{np.std(y, ddof=1):.4f}"
    )

    print(
        "Desvío estándar residual de openings: "
        f"{np.std(residuals, ddof=1):.4f}"
    )

    # --------------------------------------------------------
    # ¿EL RESIDUO SIGUE CONTENIENDO F?
    # --------------------------------------------------------

    residual_f_corr = diagnostic[
        [
            "openings_residual",
            "F",
        ]
    ].corr().iloc[0, 1]

    print(
        "\nCorrelación residual(openings | T,N) con F: "
        f"{residual_f_corr:.3f}"
    )

    # --------------------------------------------------------
    # MÉTRICA INTUITIVA DE FRAGMENTACIÓN
    # --------------------------------------------------------

    diagnostic["openings_per_session"] = (
        diagnostic["mean_daily_app_openings"]
        / diagnostic["mean_daily_session_count"]
    )

    openings_per_session_f_corr = diagnostic[
        [
            "openings_per_session",
            "F",
        ]
    ].corr().iloc[0, 1]

    print(
        "Correlación openings/session con F: "
        f"{openings_per_session_f_corr:.3f}"
    )

    print("\nResumen de openings por sesión:")

    print(
        diagnostic["openings_per_session"]
        .describe(
            percentiles=[
                0.05,
                0.50,
                0.95,
            ]
        )
        .round(3)
    )