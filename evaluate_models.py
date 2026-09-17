"""
Evaluación de modelos mediante cross-validation sobre development.

El conjunto test NO participa en selección de modelos,
hiperparámetros ni decisiones metodológicas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

from xgboost import XGBRegressor

import joblib
from pathlib import Path

import config


# ============================================================
# METADATA PARA CROSS-VALIDATION
# ============================================================

def build_development_age_labels(
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> np.ndarray:
    """Obtiene la edad de cada niño de development solo para estratificar."""

    metadata = development_dataset[
        ["child_id"]
    ].merge(
        population[
            [
                "child_id",
                "age",
            ]
        ],
        on="child_id",
        how="left",
        validate="one_to_one",
    )

    assert metadata["age"].notna().all()

    return metadata["age"].to_numpy(dtype=int)


# ============================================================
# CROSS-VALIDATION
# ============================================================

def evaluate_model_cv(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    age_labels: np.ndarray,
    model_name: str,
) -> pd.DataFrame:
    """Evalúa un modelo con 5-fold CV estratificado por edad."""

    cv = StratifiedKFold(
        n_splits=config.CV_FOLDS,
        shuffle=True,
        random_state=config.CV_SEED,
    )

    fold_results = []

    for fold_index, (train_indices, validation_indices) in enumerate(
        cv.split(X, age_labels),
        start=1,
    ):
        # Cada fold recibe una instancia independiente del modelo.
        fold_model = clone(model)

        X_train = X.iloc[train_indices]
        y_train = y.iloc[train_indices]

        X_validation = X.iloc[validation_indices]
        y_validation = y.iloc[validation_indices]

        fold_model.fit(
            X_train,
            y_train,
        )

        predictions = fold_model.predict(
            X_validation
        )

        mae = mean_absolute_error(
            y_validation,
            predictions,
        )

        rmse = root_mean_squared_error(
            y_validation,
            predictions,
        )

        r2 = r2_score(
            y_validation,
            predictions,
        )

        fold_results.append(
            {
                "model": model_name,
                "fold": fold_index,
                "train_size": len(train_indices),
                "validation_size": len(validation_indices),
                "mae": float(mae),
                "rmse": float(rmse),
                "r2": float(r2),
            }
        )

    return pd.DataFrame(fold_results)


# ============================================================
# VALIDACIÓN DE LOS FOLDS
# ============================================================

def validate_cv_folds(
    X: pd.DataFrame,
    age_labels: np.ndarray,
) -> None:
    """Verifica tamaño y balance etario de los folds."""

    print("\nVALIDACIÓN DE CROSS-VALIDATION\n")

    cv = StratifiedKFold(
        n_splits=config.CV_FOLDS,
        shuffle=True,
        random_state=config.CV_SEED,
    )

    seen_validation_indices = []

    for fold_index, (train_indices, validation_indices) in enumerate(
        cv.split(X, age_labels),
        start=1,
    ):
        # Train y validation no pueden compartir filas.
        assert len(
            set(train_indices)
            & set(validation_indices)
        ) == 0

        seen_validation_indices.extend(
            validation_indices.tolist()
        )

        validation_ages = pd.Series(
            age_labels[validation_indices]
        )

        age_counts = (
            validation_ages
            .value_counts()
            .sort_index()
        )

        # Development tiene 160 niños por edad.
        # Con 5 folds deben quedar 32 por edad en validation.
        expected_per_age = (
            config.DEVELOPMENT_CHILDREN_PER_AGE
            // config.CV_FOLDS
        )

        for age in config.AGES:
            assert (
                age_counts.loc[age]
                == expected_per_age
            )

        print(
            f"Fold {fold_index}: "
            f"train={len(train_indices)}, "
            f"validation={len(validation_indices)}"
        )

    # Cada observación debe funcionar exactamente una vez
    # como validation durante los 5 folds.
    assert len(seen_validation_indices) == len(X)

    assert len(
        set(seen_validation_indices)
    ) == len(X)

    print("Train/validation sin solapamiento: OK")
    print("32 niños por edad en cada validation fold: OK")
    print("Cada niño aparece una vez como validation: OK")


# ============================================================
# RESUMEN DE RESULTADOS
# ============================================================

def summarize_cv_results(
    results: pd.DataFrame,
) -> pd.DataFrame:
    """Resume media y dispersión de las métricas entre folds."""

    summary = (
        results
        .groupby("model")
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .round(4)
    )

    return summary


# ============================================================
# BASELINE DUMMY
# ============================================================

def evaluate_dummy_baseline(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evalúa el baseline que predice la media del target."""

    print("\nBASELINE: DUMMY REGRESSOR\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    validate_cv_folds(
        X=X_development,
        age_labels=age_labels,
    )

    baseline = DummyRegressor(
        strategy="mean"
    )

    results = evaluate_model_cv(
        model=baseline,
        X=X_development,
        y=y_development,
        age_labels=age_labels,
        model_name="DummyMean",
    )

    print("\nResultados por fold:")
    print(
        results[
            [
                "fold",
                "train_size",
                "validation_size",
                "mae",
                "rmse",
                "r2",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

    summary = summarize_cv_results(
        results
    )

    print("\nResumen CV:")
    print(summary)

    return results, summary

def evaluate_linear_regression(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evalúa Linear Regression sobre development mediante 5-fold CV."""

    print("\nMODELO: LINEAR REGRESSION\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    model = LinearRegression()

    results = evaluate_model_cv(
        model=model,
        X=X_development,
        y=y_development,
        age_labels=age_labels,
        model_name="LinearRegression",
    )

    print("Resultados por fold:")
    print(
        results[
            [
                "fold",
                "train_size",
                "validation_size",
                "mae",
                "rmse",
                "r2",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

    summary = summarize_cv_results(
        results
    )

    print("\nResumen CV:")
    print(summary)

    return results, summary

# ============================================================
# RIDGE REGRESSION
# ============================================================

def evaluate_ridge_regression(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara distintos valores de alpha para Ridge mediante CV."""

    print("\nMODELO: RIDGE REGRESSION\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    # Grilla pequeña y logarítmica predefinida.
    ridge_alphas = [
        0.01,
        0.1,
        1.0,
        10.0,
        100.0,
    ]

    all_results = []

    for alpha in ridge_alphas:

        # El scaler se ajusta dentro de cada fold gracias
        # al Pipeline, evitando leakage de validation.
        model = Pipeline(
            steps=[
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "ridge",
                    Ridge(alpha=alpha),
                ),
            ]
        )

        results = evaluate_model_cv(
            model=model,
            X=X_development,
            y=y_development,
            age_labels=age_labels,
            model_name=f"Ridge_alpha_{alpha:g}",
        )

        results["alpha"] = alpha

        all_results.append(results)

    combined_results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = (
        combined_results
        .groupby(
            [
                "model",
                "alpha",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .sort_values(
            by=[
                "mae_mean",
                "rmse_mean",
            ],
            ascending=True,
        )
        .reset_index(drop=True)
    )

    print("Resumen CV por alpha:")

    print(
        summary.round(4).to_string(
            index=False
        )
    )

    # Selección primaria por MAE.
    best_row = summary.iloc[0]

    print("\nMejor alpha según MAE medio:")

    print(
        f"alpha={best_row['alpha']:g} | "
        f"MAE={best_row['mae_mean']:.4f} | "
        f"RMSE={best_row['rmse_mean']:.4f} | "
        f"R²={best_row['r2_mean']:.4f}"
    )

    return combined_results, summary

# ============================================================
# RANDOM FOREST REGRESSION
# ============================================================

def evaluate_random_forest(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara una grilla pequeña de Random Forest mediante CV."""

    print("\nMODELO: RANDOM FOREST\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    # Número fijo de árboles suficientemente alto para reducir
    # variabilidad Monte Carlo sin convertir la búsqueda en algo enorme.
    n_estimators = 300

    # Grilla pequeña predefinida.
    max_depth_values = [
        None,
        4,
        8,
    ]

    min_samples_leaf_values = [
        1,
        5,
        10,
    ]

    all_results = []

    for max_depth in max_depth_values:

        for min_samples_leaf in min_samples_leaf_values:

            model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
                random_state=config.CV_SEED,
                n_jobs=-1,
            )

            depth_name = (
                "None"
                if max_depth is None
                else str(max_depth)
            )

            model_name = (
                f"RF_depth_{depth_name}"
                f"_leaf_{min_samples_leaf}"
            )

            results = evaluate_model_cv(
                model=model,
                X=X_development,
                y=y_development,
                age_labels=age_labels,
                model_name=model_name,
            )

            results["max_depth"] = (
                -1
                if max_depth is None
                else max_depth
            )

            results["min_samples_leaf"] = (
                min_samples_leaf
            )

            results["n_estimators"] = (
                n_estimators
            )

            all_results.append(results)

    combined_results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = (
        combined_results
        .groupby(
            [
                "model",
                "max_depth",
                "min_samples_leaf",
                "n_estimators",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .sort_values(
            by=[
                "mae_mean",
                "rmse_mean",
            ],
            ascending=True,
        )
        .reset_index(drop=True)
    )

    print("Resumen CV por configuración:")

    printable_summary = summary.copy()

    printable_summary["max_depth"] = (
        printable_summary["max_depth"]
        .replace(-1, "None")
    )

    print(
        printable_summary
        .round(4)
        .to_string(index=False)
    )

    # Regla primaria predefinida:
    # menor MAE medio en CV.
    best_row = summary.iloc[0]

    best_depth = (
        "None"
        if best_row["max_depth"] == -1
        else str(int(best_row["max_depth"]))
    )

    print("\nMejor configuración según MAE medio:")

    print(
        f"n_estimators="
        f"{int(best_row['n_estimators'])} | "
        f"max_depth={best_depth} | "
        f"min_samples_leaf="
        f"{int(best_row['min_samples_leaf'])} | "
        f"MAE={best_row['mae_mean']:.4f} | "
        f"RMSE={best_row['rmse_mean']:.4f} | "
        f"R²={best_row['r2_mean']:.4f}"
    )

    return combined_results, summary

# ============================================================
# XGBOOST REGRESSION
# ============================================================

def evaluate_xgboost(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara una grilla pequeña de XGBoost mediante CV."""

    print("\nMODELO: XGBOOST\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    # Grilla pequeña predefinida para controlar complejidad
    # sin hacer una búsqueda excesiva.
    max_depth_values = [
        2,
        3,
        4,
    ]

    learning_rate_values = [
        0.03,
        0.10,
    ]

    min_child_weight_values = [
        1,
        5,
    ]

    # Se mantiene fijo para todas las configuraciones.
    n_estimators = 300

    all_results = []

    for max_depth in max_depth_values:

        for learning_rate in learning_rate_values:

            for min_child_weight in min_child_weight_values:

                model = XGBRegressor(
                    objective="reg:squarederror",
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    min_child_weight=min_child_weight,
                    subsample=1.0,
                    colsample_bytree=1.0,
                    reg_alpha=0.0,
                    reg_lambda=1.0,
                    random_state=config.CV_SEED,
                    n_jobs=-1,
                    verbosity=0,
                )

                model_name = (
                    f"XGB_depth_{max_depth}"
                    f"_lr_{learning_rate:g}"
                    f"_child_{min_child_weight}"
                )

                results = evaluate_model_cv(
                    model=model,
                    X=X_development,
                    y=y_development,
                    age_labels=age_labels,
                    model_name=model_name,
                )

                results["max_depth"] = max_depth
                results["learning_rate"] = learning_rate
                results["min_child_weight"] = min_child_weight
                results["n_estimators"] = n_estimators

                all_results.append(results)

    combined_results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = (
        combined_results
        .groupby(
            [
                "model",
                "max_depth",
                "learning_rate",
                "min_child_weight",
                "n_estimators",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .sort_values(
            by=[
                "mae_mean",
                "rmse_mean",
            ],
            ascending=True,
        )
        .reset_index(drop=True)
    )

    print("Resumen CV por configuración:")

    print(
        summary
        .round(4)
        .to_string(index=False)
    )

    # Selección primaria predefinida:
    # menor MAE medio.
    best_row = summary.iloc[0]

    print("\nMejor configuración según MAE medio:")

    print(
        f"n_estimators="
        f"{int(best_row['n_estimators'])} | "
        f"max_depth="
        f"{int(best_row['max_depth'])} | "
        f"learning_rate="
        f"{best_row['learning_rate']:.4f} | "
        f"min_child_weight="
        f"{int(best_row['min_child_weight'])} | "
        f"MAE={best_row['mae_mean']:.4f} | "
        f"RMSE={best_row['rmse_mean']:.4f} | "
        f"R²={best_row['r2_mean']:.4f}"
    )

    return combined_results, summary

# ============================================================
# LEARNING CURVE
# ============================================================

def evaluate_learning_curve(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """
    Evalúa cómo cambia el rendimiento de Linear Regression
    al aumentar la cantidad de datos de entrenamiento.

    Todo el análisis se realiza exclusivamente sobre development.
    """

    print("\nLEARNING CURVE: LINEAR REGRESSION\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    cv = StratifiedKFold(
        n_splits=config.CV_FOLDS,
        shuffle=True,
        random_state=config.CV_SEED,
    )

    # Fracciones del training disponible dentro de cada fold.
    train_fractions = [
        0.25,
        0.50,
        0.75,
        1.00,
    ]

    all_results = []

    for fold_index, (train_indices, validation_indices) in enumerate(
        cv.split(X_development, age_labels),
        start=1,
    ):
        X_validation = X_development.iloc[
            validation_indices
        ]

        y_validation = y_development.iloc[
            validation_indices
        ]

        # Metadata correspondiente exclusivamente al training fold.
        train_ages = age_labels[train_indices]

        for fraction in train_fractions:

            # ------------------------------------------------
            # SUBMUESTRA BALANCEADA POR EDAD
            # ------------------------------------------------

            selected_indices = []

            for age in config.AGES:

                age_indices = train_indices[
                    train_ages == age
                ]

                # Cada training fold tiene 128 niños por edad.
                # Usamos exactamente la misma fracción por edad.
                n_select = int(
                    len(age_indices) * fraction
                )

                # RNG reproducible e independiente por fold,
                # fracción y edad.
                fraction_code = int(
                    round(fraction * 100)
                )

                rng = np.random.default_rng(
                    config.CV_SEED
                    + fold_index * 10_000
                    + fraction_code * 100
                    + int(age)
                )

                selected_age_indices = rng.choice(
                    age_indices,
                    size=n_select,
                    replace=False,
                )

                selected_indices.extend(
                    selected_age_indices.tolist()
                )

            selected_indices = np.array(
                selected_indices,
                dtype=int,
            )

            X_train_subset = X_development.iloc[
                selected_indices
            ]

            y_train_subset = y_development.iloc[
                selected_indices
            ]

            model = LinearRegression()

            model.fit(
                X_train_subset,
                y_train_subset,
            )

            predictions = model.predict(
                X_validation
            )

            mae = mean_absolute_error(
                y_validation,
                predictions,
            )

            rmse = root_mean_squared_error(
                y_validation,
                predictions,
            )

            r2 = r2_score(
                y_validation,
                predictions,
            )

            all_results.append(
                {
                    "fold": fold_index,
                    "train_fraction": fraction,
                    "train_size": len(
                        selected_indices
                    ),
                    "validation_size": len(
                        validation_indices
                    ),
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2),
                }
            )

    results = pd.DataFrame(
        all_results
    )

    summary = (
        results
        .groupby(
            [
                "train_fraction",
                "train_size",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .sort_values("train_fraction")
        .reset_index(drop=True)
    )

    print("Resumen por tamaño de entrenamiento:")

    print(
        summary
        .round(4)
        .to_string(index=False)
    )

    return summary

# ============================================================
# ABLATION STUDY
# ============================================================

def evaluate_feature_ablation(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """
    Evalúa el aporte predictivo incremental de grupos de features.

    Se elimina un grupo por vez y se compara el rendimiento
    contra Linear Regression con todas las features.
    """

    print("\nABLATION STUDY: LINEAR REGRESSION\n")

    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    feature_groups = {
        "age": [
            "age_scaled",
        ],
        "intensity": [
            "mean_daily_use_minutes",
            "mean_daily_session_count",
            "median_session_duration",
            "mean_daily_app_openings",
        ],
        "temporal_context": [
            "post_bedtime_use_ratio",
            "school_use_ratio",
        ],
        "categories": [
            "games_share",
            "social_share",
            "entertainment_share",
            "education_share",
        ],
    }

    # Defensa contra errores silenciosos en los nombres.
    grouped_features = {
        feature
        for features in feature_groups.values()
        for feature in features
    }

    assert grouped_features == set(config.DATASET_A_FEATURES), (
        "Los grupos del ablation no coinciden exactamente "
        "con las features de Dataset A."
    )

    experiments = {
        "Full": list(config.DATASET_A_FEATURES),
    }

    for group_name, removed_features in feature_groups.items():

        remaining_features = [
            feature
            for feature in config.DATASET_A_FEATURES
            if feature not in removed_features
        ]

        experiments[
            f"Without_{group_name}"
        ] = remaining_features

    all_results = []

    for experiment_name, selected_features in experiments.items():

        X_subset = X_development[
            selected_features
        ].copy()

        model = LinearRegression()

        results = evaluate_model_cv(
            model=model,
            X=X_subset,
            y=y_development,
            age_labels=age_labels,
            model_name=experiment_name,
        )

        results["n_features"] = len(
            selected_features
        )

        all_results.append(results)

    combined_results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = (
        combined_results
        .groupby(
            [
                "model",
                "n_features",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
    )

    # --------------------------------------------------------
    # COMPARACIÓN CONTRA FULL
    # --------------------------------------------------------

    full_row = summary.loc[
        summary["model"] == "Full"
    ].iloc[0]

    summary["delta_mae_vs_full"] = (
        summary["mae_mean"]
        - full_row["mae_mean"]
    )

    summary["delta_rmse_vs_full"] = (
        summary["rmse_mean"]
        - full_row["rmse_mean"]
    )

    summary["delta_r2_vs_full"] = (
        summary["r2_mean"]
        - full_row["r2_mean"]
    )

    # Full primero; luego ablaciones ordenadas por deterioro de MAE.
    summary["is_full"] = (
        summary["model"] == "Full"
    )

    summary = (
        summary
        .sort_values(
            by=[
                "is_full",
                "delta_mae_vs_full",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .drop(columns="is_full")
        .reset_index(drop=True)
    )

    print("Resumen de ablaciones:")

    print(
        summary
        .round(4)
        .to_string(index=False)
    )

    return summary

# ============================================================
# ORACLE DIAGNOSTIC
# ============================================================

def evaluate_oracle_models(
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
    y_development: pd.Series,
) -> pd.DataFrame:
    """
    Evalúa modelos oracle utilizando variables latentes internas.

    IMPORTANTE:
    Estos modelos son únicamente diagnósticos del DGM.
    No son candidatos para producción y sus variables nunca
    podrán formar parte de X.
    """

    print("\nDIAGNÓSTICO ORACLE\n")

    # Recupera las variables latentes en exactamente el mismo
    # orden de los niños del conjunto development.
    oracle_data = (
        development_dataset[
            ["child_id"]
        ]
        .merge(
            population[
                [
                    "child_id",
                    "S",
                    "U",
                    "B",
                    "F",
                ]
            ],
            on="child_id",
            how="left",
            validate="one_to_one",
        )
    )

    assert len(oracle_data) == len(
        development_dataset
    )

    assert oracle_data[
        [
            "S",
            "U",
            "B",
            "F",
        ]
    ].notna().all().all()

    # Edad se utiliza solamente para reproducir
    # exactamente los mismos folds del resto de modelos.
    age_labels = build_development_age_labels(
        development_dataset=development_dataset,
        population=population,
    )

    oracle_experiments = {
        "Oracle_S": [
            "S",
        ],
        "Oracle_S_U": [
            "S",
            "U",
        ],
        "Oracle_S_U_B_F": [
            "S",
            "U",
            "B",
            "F",
        ],
    }

    all_results = []

    for oracle_name, oracle_features in (
        oracle_experiments.items()
    ):

        X_oracle = oracle_data[
            oracle_features
        ].copy()

        model = LinearRegression()

        results = evaluate_model_cv(
            model=model,
            X=X_oracle,
            y=y_development,
            age_labels=age_labels,
            model_name=oracle_name,
        )

        results["n_features"] = len(
            oracle_features
        )

        all_results.append(results)

    combined_results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = (
        combined_results
        .groupby(
            [
                "model",
                "n_features",
            ],
            as_index=False,
        )
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .sort_values(
            "mae_mean"
        )
        .reset_index(drop=True)
    )

    print("Resumen de modelos oracle:")

    print(
        summary
        .round(4)
        .to_string(index=False)
    )

    return summary

# ============================================================
# AUDITORÍA DE SEÑAL OBSERVABLE DE S
# ============================================================

def audit_observable_signal_of_s(
    development_dataset: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """
    Audita cuánto de la severidad latente S aparece reflejado
    en cada feature observable del conjunto development.

    S se utiliza únicamente como diagnóstico del DGM.
    Nunca será una feature del modelo real.
    """

    print("\nAUDITORÍA DE SEÑAL OBSERVABLE DE S\n")

    diagnostic = (
        development_dataset
        .merge(
            population[
                [
                    "child_id",
                    "S",
                ]
            ],
            on="child_id",
            how="left",
            validate="one_to_one",
        )
    )

    assert diagnostic["S"].notna().all()

    # Correlación individual de cada feature observable con S.
    correlations = (
        diagnostic[
            [
                "S",
                *config.DATASET_A_FEATURES,
            ]
        ]
        .corr()["S"]
        .drop("S")
        .sort_values(
            key=lambda values: values.abs(),
            ascending=False,
        )
        .rename("corr_with_S")
        .reset_index()
        .rename(
            columns={
                "index": "feature",
            }
        )
    )

    print("Correlaciones de las features observables con S:")

    print(
        correlations
        .round(4)
        .to_string(index=False)
    )

    return correlations

# ============================================================
# FINAL TEST EVALUATION
# ============================================================

def evaluate_final_test(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[LinearRegression, pd.DataFrame]:
    """
    Entrena el modelo final seleccionado utilizando todo
    development y lo evalúa una única vez sobre test.

    IMPORTANTE:
    Test no se utiliza para selección de modelo,
    hiperparámetros ni features.
    """

    print("\nEVALUACIÓN FINAL SOBRE TEST\n")

    # --------------------------------------------------------
    # VALIDACIONES PREVIAS
    # --------------------------------------------------------

    assert list(X_development.columns) == list(
        X_test.columns
    ), (
        "Development y test no tienen las mismas features."
    )

    assert list(X_development.columns) == list(
        config.DATASET_A_FEATURES
    ), (
        "Las features del modelo final no coinciden "
        "con la whitelist de Dataset A."
    )

    assert len(X_development) == len(
        y_development
    )

    assert len(X_test) == len(
        y_test
    )

    # --------------------------------------------------------
    # MODELO FINAL
    # --------------------------------------------------------

    final_model = LinearRegression()

    final_model.fit(
        X_development,
        y_development,
    )

    predictions = final_model.predict(
        X_test
    )

    # --------------------------------------------------------
    # MÉTRICAS FINALES
    # --------------------------------------------------------

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = root_mean_squared_error(
        y_test,
        predictions,
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    results = pd.DataFrame(
        [
            {
                "model": "LinearRegression",
                "development_size": len(
                    X_development
                ),
                "test_size": len(
                    X_test
                ),
                "mae": float(mae),
                "rmse": float(rmse),
                "r2": float(r2),
            }
        ]
    )

    print(
        f"Development utilizado: "
        f"{len(X_development)} niños"
    )

    print(
        f"Test utilizado: "
        f"{len(X_test)} niños"
    )

    print("\nResultados finales:")

    print(
        results
        .round(4)
        .to_string(index=False)
    )

    return final_model, results

# ============================================================
# MODEL PERSISTENCE
# ============================================================

def save_final_model(
    final_model: LinearRegression,
    output_path: str = "models/pmu_linear_v1.joblib",
) -> None:
    """
    Guarda el modelo final del MVP junto con el contrato
    mínimo necesario para realizar inferencia posteriormente.
    """

    print("\nGUARDADO DEL MODELO FINAL\n")

    model_path = Path(output_path)

    model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = {
        "model": final_model,
        "model_version": "1.0",
        "model_type": "LinearRegression",
        "features": list(
            config.DATASET_A_FEATURES
        ),
        "n_features": len(
            config.DATASET_A_FEATURES
        ),
        "target": "synthetic_pmu_severity",
        "target_range": [
            config.TARGET_MIN,
            config.TARGET_MAX,
        ],
        "training_population": "synthetic",
        "development_size": 1120,
        "test_size": 280,
    }

    joblib.dump(
        artifact,
        model_path,
    )

    assert model_path.exists()

    print(
        f"Modelo guardado correctamente en: "
        f"{model_path}"
    )

    print(
        f"Versión: "
        f"{artifact['model_version']}"
    )

    print(
        f"Features esperadas: "
        f"{artifact['n_features']}"
    )

# ============================================================
# MODEL RELOAD VALIDATION
# ============================================================

def validate_saved_model(
    final_model: LinearRegression,
    X_reference: pd.DataFrame,
    model_path: str = "models/pmu_linear_v1.joblib",
) -> None:
    """
    Recarga el artefacto desde disco y comprueba que produzca
    exactamente las mismas predicciones que el modelo original.
    """

    print("\nVALIDACIÓN DEL MODELO GUARDADO\n")

    artifact = joblib.load(
        model_path
    )

    # --------------------------------------------------------
    # VALIDACIÓN DEL CONTRATO
    # --------------------------------------------------------

    required_keys = {
        "model",
        "model_version",
        "model_type",
        "features",
        "n_features",
        "target",
        "target_range",
        "training_population",
        "development_size",
        "test_size",
    }

    assert required_keys.issubset(
        artifact.keys()
    )

    assert (
        artifact["features"]
        == list(config.DATASET_A_FEATURES)
    )

    assert (
        artifact["n_features"]
        == len(config.DATASET_A_FEATURES)
    )

    # --------------------------------------------------------
    # PREDICCIONES
    # --------------------------------------------------------

    loaded_model = artifact["model"]

    # Utiliza una pequeña muestra únicamente para validar
    # serialización y carga del modelo.
    X_sample = (
        X_reference
        .head(20)
        .copy()
    )

    original_predictions = (
        final_model.predict(
            X_sample
        )
    )

    loaded_predictions = (
        loaded_model.predict(
            X_sample
        )
    )

    assert np.allclose(
        original_predictions,
        loaded_predictions,
        rtol=1e-12,
        atol=1e-12,
    )

    print("Artefacto cargado correctamente: OK")
    print("Contrato de 11 features conservado: OK")
    print("Predicciones antes/después de guardar: idénticas")
    print(
        f"Versión cargada: "
        f"{artifact['model_version']}"
    )