"""
Generación de la población sintética del DGM v1.0.

Este módulo genera únicamente variables de nivel niño:
- edad,
- variables latentes S, B, F y U,
- modalidad y horario escolar,
- bedtime habitual.

No genera todavía comportamiento diario, sesiones ni features del ML.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# ============================================================
# FUNCIONES AUXILIARES DE HORARIO
# ============================================================

def clock_to_minutes(clock: str) -> int:
    """Convierte una hora HH:MM a minutos desde las 00:00."""
    hours, minutes = map(int, clock.split(":"))
    return hours * 60 + minutes


def minutes_to_clock(minutes: int) -> str:
    """Convierte minutos a HH:MM, indicando si cruza al día siguiente."""
    day_offset, minute_of_day = divmod(int(minutes), 24 * 60)

    hours, mins = divmod(minute_of_day, 60)
    clock = f"{hours:02d}:{mins:02d}"

    if day_offset > 0:
        return f"{clock} (+{day_offset}d)"

    return clock


# ============================================================
# EDAD
# ============================================================

def generate_ages(n_children: int, rng: np.random.Generator) -> np.ndarray:
    """Genera edades 6-12 de forma aproximadamente balanceada."""
    ages = np.resize(np.array(config.AGES), n_children)

    # Mezcla el orden para que child_id no quede ordenado por edad.
    rng.shuffle(ages)

    return ages


def scale_age(age: np.ndarray) -> np.ndarray:
    """Transforma edad mediante la regla (age - 9) / 2."""
    return (age - 9.0) / 2.0


# ============================================================
# VARIABLES LATENTES
# ============================================================

def generate_latent_variables(
    n_children: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Genera las variables latentes independientes S, B, F y U."""
    return {
        "S": rng.normal(
            config.LATENT_MEAN,
            config.LATENT_STD,
            n_children,
        ),
        "B": rng.normal(
            config.LATENT_MEAN,
            config.LATENT_STD,
            n_children,
        ),
        "F": rng.normal(
            config.LATENT_MEAN,
            config.LATENT_STD,
            n_children,
        ),
        "U": rng.normal(
            config.LATENT_MEAN,
            config.LATENT_STD,
            n_children,
        ),
    }


# ============================================================
# CONTEXTO ESCOLAR
# ============================================================

def generate_school_modes(
    n_children: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Asigna morning, afternoon o full_day según las proporciones Base."""
    probabilities = [
        config.SCHOOL_MODE_PROBABILITIES[mode]
        for mode in config.SCHOOL_MODES
    ]

    return rng.choice(
        config.SCHOOL_MODES,
        size=n_children,
        p=probabilities,
    )


def generate_school_schedule(
    school_mode: str,
    rng: np.random.Generator,
) -> tuple[int, int, int]:
    """Genera inicio y fin escolar preservando la duración de la jornada."""
    base_schedule = config.SCHOOL_BASE_SCHEDULES[school_mode]

    base_start = clock_to_minutes(base_schedule["start"])
    base_end = clock_to_minutes(base_schedule["end"])

    # El mismo desplazamiento se aplica al inicio y al fin.
    shift = rng.integers(
        config.SCHOOL_TIME_SHIFT_MIN_MINUTES,
        config.SCHOOL_TIME_SHIFT_MAX_MINUTES + 1,
    )

    school_start = base_start + int(shift)
    school_end = base_end + int(shift)

    return school_start, school_end, int(shift)


# ============================================================
# BEDTIME
# ============================================================

def generate_bedtime(
    rng: np.random.Generator,
) -> tuple[int, int, int]:
    """Genera bedtime escolar y bedtime para noches sin colegio."""
    school_min = clock_to_minutes(config.BEDTIME_SCHOOL_MIN)
    school_max = clock_to_minutes(config.BEDTIME_SCHOOL_MAX)

    bedtime_school = int(
        rng.integers(
            school_min,
            school_max + 1,
        )
    )

    delay = int(
        rng.integers(
            config.NON_SCHOOL_BEDTIME_DELAY_MIN_MINUTES,
            config.NON_SCHOOL_BEDTIME_DELAY_MAX_MINUTES + 1,
        )
    )

    # Puede superar 1440: eso representa una hora del día siguiente.
    bedtime_non_school = bedtime_school + delay

    return bedtime_school, bedtime_non_school, delay


# ============================================================
# GENERACIÓN DE POBLACIÓN
# ============================================================

def generate_population(
    n_children: int,
    seed: int | np.random.SeedSequence,
) -> pd.DataFrame:
    """Genera la población sintética completa a nivel niño."""
    rng = np.random.default_rng(seed)

    child_ids = np.arange(1, n_children + 1)

    ages = generate_ages(n_children, rng)
    age_scaled = scale_age(ages)

    latent = generate_latent_variables(n_children, rng)

    school_modes = generate_school_modes(n_children, rng)

    rows = []

    for index in range(n_children):
        school_start, school_end, school_shift = generate_school_schedule(
            school_modes[index],
            rng,
        )

        (
            bedtime_school,
            bedtime_non_school,
            bedtime_delay,
        ) = generate_bedtime(rng)

        rows.append(
            {
                "child_id": int(child_ids[index]),
                "age": int(ages[index]),
                "age_scaled": float(age_scaled[index]),

                # Variables internas del DGM.
                "S": float(latent["S"][index]),
                "B": float(latent["B"][index]),
                "F": float(latent["F"][index]),
                "U": float(latent["U"][index]),

                # Contexto escolar.
                "school_mode": school_modes[index],
                "school_start_minute": school_start,
                "school_end_minute": school_end,
                "school_shift_minutes": school_shift,

                # Versiones legibles para inspección humana.
                "school_start": minutes_to_clock(school_start),
                "school_end": minutes_to_clock(school_end),

                # Bedtime contextual.
                "bedtime_school_minute": bedtime_school,
                "bedtime_non_school_minute": bedtime_non_school,
                "bedtime_non_school_delay_minutes": bedtime_delay,

                # Versiones legibles.
                "bedtime_school": minutes_to_clock(bedtime_school),
                "bedtime_non_school": minutes_to_clock(
                    bedtime_non_school
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# EJECUCIÓN DE DEBUG
# ============================================================

def validate_population(population: pd.DataFrame) -> None:
    """Muestra controles estadísticos básicos de la población generada."""

    print("\nVALIDACIÓN DE POBLACIÓN\n")

    # Cantidad de niños por edad.
    print("Niños por edad:")
    print(population["age"].value_counts().sort_index())

    # Distribución de modalidades escolares.
    print("\nModalidades escolares:")
    print(
        population["school_mode"]
        .value_counts(normalize=True)
        .sort_index()
    )

    # Resumen de las variables latentes.
    print("\nResumen de variables latentes:")
    print(
        population[["S", "B", "F", "U"]]
        .agg(["mean", "std"])
        .round(3)
    )

    # Correlaciones muestrales entre variables que fueron
    # generadas independientemente.
    print("\nCorrelaciones entre variables latentes:")
    print(
        population[["S", "B", "F", "U"]]
        .corr()
        .round(3)
    )

def main() -> None:
    """Genera una muestra pequeña para inspeccionar la población."""
    population = generate_population(
        n_children=config.DEBUG_N_CHILDREN,
        seed=config.CALIBRATION_SEED,
    )

    # Verifica invariantes básicas de la población antes de continuar.
    assert population["age"].between(
        config.MIN_AGE,
        config.MAX_AGE,
    ).all()

    assert population["school_shift_minutes"].between(
        config.SCHOOL_TIME_SHIFT_MIN_MINUTES,
        config.SCHOOL_TIME_SHIFT_MAX_MINUTES,
    ).all()

    assert (
        population["bedtime_non_school_minute"]
        >= population["bedtime_school_minute"]
    ).all()

    assert population["bedtime_non_school_delay_minutes"].between(
        config.NON_SCHOOL_BEDTIME_DELAY_MIN_MINUTES,
        config.NON_SCHOOL_BEDTIME_DELAY_MAX_MINUTES,
    ).all()

    print("\nInvariantes básicas: OK")

    # Permite ver todas las columnas durante la prueba manual.
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)

    print("\nPOBLACIÓN DEBUG\n")
    # Muestra una selección de columnas para facilitar la inspección manual.
    debug_columns = [
        "child_id",
        "age",
        "age_scaled",
        "S",
        "B",
        "F",
        "U",
        "school_mode",
        "school_start",
        "school_end",
        "school_shift_minutes",
        "bedtime_school",
        "bedtime_non_school",
        "bedtime_non_school_delay_minutes",
    ]

    print(population[debug_columns].to_string(index=False))

    output_path = config.PILOT_DATA_DIR / "population_debug.csv"
    population.to_csv(output_path, index=False)

    print(f"\nArchivo guardado en: {output_path}")

    # Genera una muestra grande únicamente para validar
    # las propiedades estadísticas de la población.
    validation_population = generate_population(
        n_children=config.N_CHILDREN_FINAL,
        seed=config.CALIBRATION_SEED,
    )

    validate_population(validation_population)


if __name__ == "__main__":
    main()