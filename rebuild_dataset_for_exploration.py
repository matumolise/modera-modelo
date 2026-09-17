from __future__ import annotations

import numpy as np

import config

from generate_population import generate_population

from generate_behavior import (
    generate_daily_contexts,
    add_daily_use_time,
    add_daily_session_count,
    build_session_table,
    schedule_all_sessions,
    add_contextual_overlaps,
    build_app_episode_table,
    generate_child_category_preferences,
    assign_episode_categories,
)

from build_features import build_weekly_features
from generate_target import generate_synthetic_target
from build_dataset import build_dataset_a


def main() -> None:
    print("Reconstruyendo Dataset A...")

    # Misma realización utilizada por el pipeline original.
    seed_sequence = np.random.SeedSequence(
        config.CALIBRATION_SEED + 1
    )

    (
        population_seed,
        context_seed,
        time_seed,
        session_seed,
        duration_seed,
        scheduler_seed,
        episode_seed,
        category_seed,
        target_seed,
    ) = seed_sequence.spawn(9)

    # --------------------------------------------------------
    # 1. Población
    # --------------------------------------------------------

    population = generate_population(
        n_children=config.N_CHILDREN_FINAL,
        seed=population_seed,
    )

    # --------------------------------------------------------
    # 2. Contexto diario
    # --------------------------------------------------------

    contexts = generate_daily_contexts(
        population=population,
        seed=context_seed,
        n_days=config.N_DAYS,
    )

    # --------------------------------------------------------
    # 3. Tiempo de uso
    # --------------------------------------------------------

    time_rng = np.random.default_rng(time_seed)

    daily_behavior = add_daily_use_time(
        contexts=contexts,
        population=population,
        rng=time_rng,
    )

    # --------------------------------------------------------
    # 4. Cantidad de sesiones
    # --------------------------------------------------------

    session_rng = np.random.default_rng(session_seed)

    daily_behavior = add_daily_session_count(
        daily_behavior=daily_behavior,
        population=population,
        rng=session_rng,
    )

    # --------------------------------------------------------
    # 5. Duración de sesiones
    # --------------------------------------------------------

    duration_rng = np.random.default_rng(duration_seed)

    sessions = build_session_table(
        daily_behavior=daily_behavior,
        rng=duration_rng,
    )

    # --------------------------------------------------------
    # 6. Calendarización
    # --------------------------------------------------------

    scheduler_rng = np.random.default_rng(scheduler_seed)

    scheduled_sessions = schedule_all_sessions(
        sessions=sessions,
        daily_behavior=daily_behavior,
        rng=scheduler_rng,
        show_progress=False,
    )

    scheduled_sessions = add_contextual_overlaps(
        scheduled_sessions=scheduled_sessions,
        daily_behavior=daily_behavior,
    )

    # --------------------------------------------------------
    # 7. Episodios / aperturas
    # --------------------------------------------------------

    episode_rng = np.random.default_rng(episode_seed)

    app_episodes = build_app_episode_table(
        scheduled_sessions=scheduled_sessions,
        daily_behavior=daily_behavior,
        rng=episode_rng,
    )

    # --------------------------------------------------------
    # 8. Categorías
    # --------------------------------------------------------

    category_rng = np.random.default_rng(category_seed)

    category_preferences = generate_child_category_preferences(
        daily_behavior=daily_behavior,
        rng=category_rng,
    )

    app_episodes = assign_episode_categories(
        app_episodes=app_episodes,
        category_preferences=category_preferences,
        rng=category_rng,
    )

    # --------------------------------------------------------
    # 9. Features semanales
    # --------------------------------------------------------

    features = build_weekly_features(
        daily_behavior=daily_behavior,
        scheduled_sessions=scheduled_sessions,
        app_episodes=app_episodes,
    )

    # --------------------------------------------------------
    # 10. Target sintético
    # --------------------------------------------------------

    target_rng = np.random.default_rng(target_seed)

    target = generate_synthetic_target(
        population=population,
        rng=target_rng,
    )

    # --------------------------------------------------------
    # 11. Dataset A
    # --------------------------------------------------------

    dataset_a = build_dataset_a(
        features=features,
        target_data=target,
    )

    # --------------------------------------------------------
    # Guardado para análisis
    # --------------------------------------------------------

    config.FINAL_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        config.FINAL_DATA_DIR
        / "dataset_a_recreated.csv"
    )

    dataset_a.to_csv(
        output_path,
        index=False,
    )

    print()
    print("Dataset reconstruido correctamente.")
    print(f"Filas: {len(dataset_a)}")
    print(f"Columnas: {len(dataset_a.columns)}")
    print(f"Guardado en: {output_path}")

    print()
    print("Primeras filas:")
    print(dataset_a.head().to_string(index=False))


if __name__ == "__main__":
    main()