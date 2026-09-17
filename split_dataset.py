"""
Split development/test del Dataset A.

La separación se realiza a nivel niño y de forma estratificada
por edad. El conjunto test queda reservado para la evaluación final.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ============================================================
# SPLIT DEVELOPMENT / TEST
# ============================================================

def split_dataset_by_age(
    dataset: pd.DataFrame,
    population: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide Dataset A en development y test balanceados por edad."""

    # age se utiliza únicamente para estratificar.
    split_metadata = dataset[
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

    assert split_metadata["age"].notna().all()

    rng = np.random.default_rng(seed)

    development_ids = []
    test_ids = []

    for age in config.AGES:

        age_child_ids = (
            split_metadata.loc[
                split_metadata["age"] == age,
                "child_id",
            ]
            .to_numpy(dtype=int)
            .copy()
        )

        expected_total = (
            config.DEVELOPMENT_CHILDREN_PER_AGE
            + config.TEST_CHILDREN_PER_AGE
        )

        if len(age_child_ids) != expected_total:
            raise ValueError(
                f"Edad {age}: se esperaban "
                f"{expected_total} niños, "
                f"pero se encontraron {len(age_child_ids)}."
            )

        # Mezcla reproducible dentro de cada edad.
        rng.shuffle(age_child_ids)

        test_age_ids = age_child_ids[
            :config.TEST_CHILDREN_PER_AGE
        ]

        development_age_ids = age_child_ids[
            config.TEST_CHILDREN_PER_AGE:
        ]

        test_ids.extend(test_age_ids.tolist())
        development_ids.extend(
            development_age_ids.tolist()
        )

    development = (
        dataset.loc[
            dataset["child_id"].isin(development_ids)
        ]
        .copy()
        .sort_values("child_id")
        .reset_index(drop=True)
    )

    test = (
        dataset.loc[
            dataset["child_id"].isin(test_ids)
        ]
        .copy()
        .sort_values("child_id")
        .reset_index(drop=True)
    )

    return development, test


# ============================================================
# VALIDACIÓN DEL SPLIT
# ============================================================

def validate_dataset_split(
    development: pd.DataFrame,
    test: pd.DataFrame,
    population: pd.DataFrame,
) -> None:
    """Verifica tamaño, estratificación y separación entre conjuntos."""

    print("\nVALIDACIÓN DEL SPLIT DEVELOPMENT / TEST\n")

    # --------------------------------------------------------
    # TAMAÑOS
    # --------------------------------------------------------

    assert len(development) == config.N_DEVELOPMENT_CHILDREN
    assert len(test) == config.N_TEST_CHILDREN

    assert development["child_id"].is_unique
    assert test["child_id"].is_unique

    # --------------------------------------------------------
    # AUSENCIA DE LEAKAGE ENTRE CONJUNTOS
    # --------------------------------------------------------

    development_ids = set(
        development["child_id"]
    )

    test_ids = set(
        test["child_id"]
    )

    overlap = development_ids & test_ids

    assert len(overlap) == 0, (
        "Hay child_id presentes simultáneamente "
        "en development y test."
    )

    # La unión debe recuperar los 1400 niños.
    all_ids = development_ids | test_ids

    assert len(all_ids) == config.N_CHILDREN_FINAL

    # --------------------------------------------------------
    # BALANCE EXACTO POR EDAD
    # --------------------------------------------------------

    population_age = population[
        [
            "child_id",
            "age",
        ]
    ]

    development_with_age = development[
        ["child_id"]
    ].merge(
        population_age,
        on="child_id",
        validate="one_to_one",
    )

    test_with_age = test[
        ["child_id"]
    ].merge(
        population_age,
        on="child_id",
        validate="one_to_one",
    )

    development_counts = (
        development_with_age["age"]
        .value_counts()
        .sort_index()
    )

    test_counts = (
        test_with_age["age"]
        .value_counts()
        .sort_index()
    )

    for age in config.AGES:

        assert (
            development_counts.loc[age]
            == config.DEVELOPMENT_CHILDREN_PER_AGE
        )

        assert (
            test_counts.loc[age]
            == config.TEST_CHILDREN_PER_AGE
        )

    # --------------------------------------------------------
    # COLUMNAS
    # --------------------------------------------------------

    assert list(development.columns) == list(test.columns)

    expected_columns = [
        "child_id",
        *config.DATASET_A_FEATURES,
        "synthetic_pmu_severity",
    ]

    assert list(development.columns) == expected_columns

    print(
        f"Development: {len(development)} niños"
    )
    print(
        f"Test: {len(test)} niños"
    )
    print("child_id únicos: OK")
    print("Development/Test sin niños compartidos: OK")
    print("Unión recupera los 1400 niños: OK")
    print("160 niños por edad en development: OK")
    print("40 niños por edad en test: OK")
    print("Columnas idénticas y correctas: OK")

    print("\nNiños por edad - DEVELOPMENT:")
    print(development_counts)

    print("\nNiños por edad - TEST:")
    print(test_counts)


# ============================================================
# SEPARACIÓN X / y DE CADA CONJUNTO
# ============================================================

def build_model_matrices(
    dataset: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Construye X e y sin incluir child_id."""

    X = dataset[
        config.DATASET_A_FEATURES
    ].copy()

    y = dataset[
        "synthetic_pmu_severity"
    ].copy()

    return X, y


def validate_model_matrices(
    X_development: pd.DataFrame,
    y_development: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> None:
    """Verifica dimensiones y whitelist de matrices para ML."""

    print("\nVALIDACIÓN DE MATRICES DEVELOPMENT / TEST\n")

    assert X_development.shape == (
        config.N_DEVELOPMENT_CHILDREN,
        len(config.DATASET_A_FEATURES),
    )

    assert X_test.shape == (
        config.N_TEST_CHILDREN,
        len(config.DATASET_A_FEATURES),
    )

    assert len(y_development) == config.N_DEVELOPMENT_CHILDREN
    assert len(y_test) == config.N_TEST_CHILDREN

    assert (
        list(X_development.columns)
        == config.DATASET_A_FEATURES
    )

    assert (
        list(X_test.columns)
        == config.DATASET_A_FEATURES
    )

    # Segunda defensa explícita contra leakage.
    forbidden_dev = (
        set(config.FORBIDDEN_MODEL_FEATURES)
        & set(X_development.columns)
    )

    forbidden_test = (
        set(config.FORBIDDEN_MODEL_FEATURES)
        & set(X_test.columns)
    )

    assert len(forbidden_dev) == 0
    assert len(forbidden_test) == 0

    print(
        f"X development: {X_development.shape}"
    )
    print(
        f"X test: {X_test.shape}"
    )
    print(
        f"y development: {len(y_development)}"
    )
    print(
        f"y test: {len(y_test)}"
    )
    print("Whitelist idéntica en ambos conjuntos: OK")
    print("Sin variables prohibidas en X: OK")