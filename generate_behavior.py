"""
Generación del comportamiento diario del DGM v1.0.

Este módulo construye progresivamente:
- contexto diario,
- tiempo total de uso,
- cantidad de sesiones,
- duraciones,
- scheduling,
- episodios de aplicaciones,
- categorías,
- target sintético.

En esta primera versión solo se implementa el contexto diario.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config


# ============================================================
# ESTRUCTURA DE CONTEXTO DIARIO
# ============================================================

@dataclass
class DailyContext:
    """Representa el contexto temporal de un niño en un día concreto."""

    child_id: int
    day_index: int
    weekday: int
    is_weekend: bool

    has_school_today: bool
    has_school_next_day: bool

    school_start_minute: int | None
    school_end_minute: int | None

    bedtime_minute: int
    previous_bedtime_minute: int
    day_start_minute: int


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def is_school_day(weekday: int) -> bool:
    """Indica si un weekday corresponde a día escolar en Base v1."""
    return weekday in config.SCHOOL_WEEKDAYS


def is_weekend_day(weekday: int) -> bool:
    """Indica si un weekday corresponde a sábado o domingo."""
    return weekday in (5, 6)


def get_next_weekday(weekday: int) -> int:
    """Devuelve el weekday del día siguiente."""
    return (weekday + 1) % 7


# ============================================================
# BEDTIME
# ============================================================

def select_bedtime(
    child: pd.Series,
    has_school_next_day: bool,
) -> int:
    """Selecciona el bedtime correspondiente al contexto de la noche."""
    if has_school_next_day:
        return int(child["bedtime_school_minute"])

    return int(child["bedtime_non_school_minute"])


# ============================================================
# DAY START
# ============================================================

def generate_day_start(
    child: pd.Series,
    has_school_today: bool,
    rng: np.random.Generator,
) -> int:
    """Genera el inicio operativo del día según escuela y contexto."""

    school_mode = child["school_mode"]

    # Si hay colegio y el niño va a turno mañana o jornada completa,
    # day_start se ubica entre 60 y 90 minutos antes del ingreso.
    if has_school_today and school_mode in ("morning", "full_day"):
        offset = int(
            rng.integers(
                config.DAY_START_BEFORE_SCHOOL_MIN_MINUTES,
                config.DAY_START_BEFORE_SCHOOL_MAX_MINUTES + 1,
            )
        )

        return int(child["school_start_minute"]) - offset

    # Si hay colegio pero el turno es tarde,
    # se usa un rango operativo de mañana independiente.
    if has_school_today and school_mode == "afternoon":
        min_start = _clock_to_minutes(config.DAY_START_AFTERNOON_MIN)
        max_start = _clock_to_minutes(config.DAY_START_AFTERNOON_MAX)

        return int(rng.integers(min_start, max_start + 1))

    # Si no hay colegio, se usa el rango de fin de semana/día libre.
    min_start = _clock_to_minutes(config.DAY_START_NO_SCHOOL_MIN)
    max_start = _clock_to_minutes(config.DAY_START_NO_SCHOOL_MAX)

    return int(rng.integers(min_start, max_start + 1))


def _clock_to_minutes(clock: str) -> int:
    """Convierte una hora HH:MM a minutos desde las 00:00."""
    hours, minutes = map(int, clock.split(":"))
    return hours * 60 + minutes


def minutes_to_clock(minutes: float) -> str:
    """Convierte minutos desde medianoche a HH:MM para inspección."""
    day_offset, minute_of_day = divmod(int(minutes), 24 * 60)

    hours, mins = divmod(minute_of_day, 60)
    clock = f"{hours:02d}:{mins:02d}"

    if day_offset > 0:
        return f"{clock} (+{day_offset}d)"

    return clock


# ============================================================
# CONTEXTO DIARIO
# ============================================================

@dataclass
class TimeWindow:
    """Representa una ventana temporal interna del scheduler."""

    name: str
    start_minute: float
    end_minute: float
    weight: float

    @property
    def duration_minutes(self) -> float:
        """Devuelve la duración de la ventana en minutos."""
        return self.end_minute - self.start_minute

def build_daily_context(
    child: pd.Series,
    day_index: int,
    rng: np.random.Generator,
) -> DailyContext:
    """Construye el contexto temporal completo de un día."""

    # Base v1 comienza un lunes.
    weekday = day_index % 7

    has_school_today = is_school_day(weekday)

    next_weekday = get_next_weekday(weekday)
    has_school_next_day = is_school_day(next_weekday)

    bedtime_minute = select_bedtime(
        child,
        has_school_next_day,
    )

    # El bedtime de la noche anterior depende de si HOY hay colegio.
    previous_bedtime_minute = select_bedtime(
        child,
        has_school_today,
    )

    day_start_minute = generate_day_start(
        child,
        has_school_today,
        rng,
    )

    if has_school_today:
        school_start = int(child["school_start_minute"])
        school_end = int(child["school_end_minute"])
    else:
        school_start = None
        school_end = None

    return DailyContext(
        child_id=int(child["child_id"]),
        day_index=day_index,
        weekday=weekday,
        is_weekend=is_weekend_day(weekday),

        has_school_today=has_school_today,
        has_school_next_day=has_school_next_day,

        school_start_minute=school_start,
        school_end_minute=school_end,

        bedtime_minute=bedtime_minute,
        day_start_minute=day_start_minute,
        previous_bedtime_minute=previous_bedtime_minute,
    )


def generate_daily_contexts(
    population: pd.DataFrame,
    seed: int,
    n_days: int = config.N_DAYS,
) -> pd.DataFrame:
    """Genera el contexto diario para todos los niños."""

    rng = np.random.default_rng(seed)

    rows = []

    for _, child in population.iterrows():
        for day_index in range(n_days):
            context = build_daily_context(
                child,
                day_index,
                rng,
            )

            rows.append(
                {
                    "child_id": context.child_id,
                    "day_index": context.day_index,
                    "weekday": context.weekday,
                    "is_weekend": context.is_weekend,

                    "has_school_today": context.has_school_today,
                    "has_school_next_day": context.has_school_next_day,

                    "school_start_minute": context.school_start_minute,
                    "school_end_minute": context.school_end_minute,

                    "bedtime_minute": context.bedtime_minute,
                    "previous_bedtime_minute": context.previous_bedtime_minute,
                    "day_start_minute": context.day_start_minute,

                    # Columnas legibles para inspección humana.
                    "school_start": (
                        minutes_to_clock(context.school_start_minute)
                        if context.school_start_minute is not None
                        else None
                    ),
                    "school_end": (
                        minutes_to_clock(context.school_end_minute)
                        if context.school_end_minute is not None
                        else None
                    ),
                    "bedtime": minutes_to_clock(
                        context.bedtime_minute
                    ),
                    "day_start": minutes_to_clock(
                        context.day_start_minute
                    ),
                    "previous_bedtime": minutes_to_clock(
                        context.previous_bedtime_minute
                    ),
                }
            )

    return pd.DataFrame(rows)

# ============================================================
# TIEMPO TOTAL DE USO DIARIO
# ============================================================

def calculate_time_latent_score(child: pd.Series) -> float:
    """Calcula el predictor latente B>S>edad usado para generar T."""
    return (
        config.TIME_WEIGHT_B * float(child["B"])
        + config.TIME_WEIGHT_S * float(child["S"])
        + config.TIME_WEIGHT_AGE * float(child["age_scaled"])
    )


def generate_daily_use_minutes(
    child: pd.Series,
    is_weekend: bool,
    rng: np.random.Generator,
) -> float:
    """Genera el tiempo total de uso diario mediante una Lognormal."""
    latent_score = calculate_time_latent_score(child)

    weekend_effect = (
        config.TIME_WEEKEND_EFFECT
        if is_weekend
        else 0.0
    )

    # log(T) = alpha_T + kappa_T*L_T
    #          + efecto_weekend + sigma_day*Z
    log_time = (
        config.TIME_ALPHA
        + config.TIME_KAPPA * latent_score
        + weekend_effect
        + config.TIME_DAILY_SIGMA * rng.normal()
    )

    daily_minutes = float(np.exp(log_time))

    # Una realización físicamente imposible se remuestrea.
    # No constituye un cutoff clínico.
    while daily_minutes >= config.MAX_DAILY_MINUTES:
        log_time = (
            config.TIME_ALPHA
            + config.TIME_KAPPA * latent_score
            + weekend_effect
            + config.TIME_DAILY_SIGMA * rng.normal()
        )

        daily_minutes = float(np.exp(log_time))

    return daily_minutes

def add_daily_use_time(
    contexts: pd.DataFrame,
    population: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Agrega el tiempo total de uso T a cada niño-día."""
    result = contexts.merge(
        population[
            [
                "child_id",
                "age",
                "age_scaled",
                "S",
                "B",
            ]
        ],
        on="child_id",
        how="left",
        validate="many_to_one",
    )

    daily_minutes = []

    for _, row in result.iterrows():
        daily_minutes.append(
            generate_daily_use_minutes(
                child=row,
                is_weekend=bool(row["is_weekend"]),
                rng=rng,
            )
        )

    result["daily_use_minutes"] = daily_minutes

    return result

def validate_daily_use_time(
    daily_behavior: pd.DataFrame,
) -> None:
    """Muestra controles estadísticos del tiempo diario T."""

    print("\nVALIDACIÓN DE TIEMPO DIARIO\n")

    print("Resumen general de T:")
    print(
        daily_behavior["daily_use_minutes"]
        .describe(
            percentiles=[0.05, 0.25, 0.50, 0.75, 0.95]
        )
        .round(1)
    )

    print("\nT promedio por edad:")
    print(
        daily_behavior
        .groupby("age")["daily_use_minutes"]
        .mean()
        .round(1)
    )

    print("\nT promedio weekday vs weekend:")
    print(
        daily_behavior
        .groupby("is_weekend")["daily_use_minutes"]
        .mean()
        .round(1)
    )

    print("\nCorrelaciones latentes con T:")
    print(
        daily_behavior[
            [
                "daily_use_minutes",
                "B",
                "S",
                "age_scaled",
                "F",
            ]
        ]
        .corr()["daily_use_minutes"]
        .round(3)
    )

def validate_daily_session_count(
    daily_behavior: pd.DataFrame,
) -> None:
    """Muestra controles estadísticos de la cantidad diaria de sesiones."""

    print("\nVALIDACIÓN DE SESIONES DIARIAS\n")

    print("Resumen general de N:")
    print(
        daily_behavior["daily_session_count"]
        .describe(
            percentiles=[0.05, 0.25, 0.50, 0.75, 0.95]
        )
        .round(1)
    )

    print("\nN promedio por edad:")
    print(
        daily_behavior
        .groupby("age")["daily_session_count"]
        .mean()
        .round(1)
    )

    print("\nN promedio weekday vs weekend:")
    print(
        daily_behavior
        .groupby("is_weekend")["daily_session_count"]
        .mean()
        .round(1)
    )

    print("\nCorrelaciones latentes con N:")
    print(
        daily_behavior[
            [
                "daily_session_count",
                "F",
                "B",
                "S",
            ]
        ]
        .corr()["daily_session_count"]
        .round(3)
    )

    print("\nCorrelación T-N:")
    print(
        daily_behavior[
            [
                "daily_use_minutes",
                "daily_session_count",
            ]
        ]
        .corr()
        .round(3)
    )

# ============================================================
# VALIDACIÓN
# ============================================================

def validate_daily_contexts(contexts: pd.DataFrame) -> None:
    """Verifica invariantes básicas del contexto diario."""

    # Cada niño debe tener exactamente n_days filas.
    counts = contexts.groupby("child_id").size()

    assert (counts == config.N_DAYS).all()

    # Weekend debe ser exactamente sábado/domingo.
    expected_weekend = contexts["weekday"].isin([5, 6])

    assert (
        contexts["is_weekend"]
        == expected_weekend
    ).all()

    # Cuando no hay colegio, no debe existir horario escolar activo.
    no_school = ~contexts["has_school_today"]

    assert contexts.loc[
        no_school,
        "school_start_minute",
    ].isna().all()

    assert contexts.loc[
        no_school,
        "school_end_minute",
    ].isna().all()

    # Cuando sí hay colegio, inicio y fin deben existir.
    school = contexts["has_school_today"]

    assert contexts.loc[
        school,
        "school_start_minute",
    ].notna().all()

    assert contexts.loc[
        school,
        "school_end_minute",
    ].notna().all()

    # day_start siempre debe quedar dentro del día calendario.
    assert contexts["day_start_minute"].between(
        0,
        24 * 60 - 1,
    ).all()

    print("\nInvariantes de contexto diario: OK")

# ============================================================
# CANTIDAD DIARIA DE SESIONES
# ============================================================

def calculate_session_latent_score(child: pd.Series) -> float:
    """Calcula el predictor latente F>B>S usado para generar N."""
    return (
        config.SESSION_WEIGHT_F * float(child["F"])
        + config.SESSION_WEIGHT_B * float(child["B"])
        + config.SESSION_WEIGHT_S * float(child["S"])
    )


def sample_negative_binomial_nb2(
    mu: float,
    r: float,
    rng: np.random.Generator,
) -> int:
    """Muestrea una NB2 parametrizada por media mu y dispersión r."""
    # NumPy usa la parametrización NB(n, p):
    # media = n * (1 - p) / p
    # Por lo tanto, para NB2 con media mu y dispersión r:
    # p = r / (r + mu)
    p = r / (r + mu)

    return int(
        rng.negative_binomial(
            n=r,
            p=p,
        )
    )


def generate_daily_session_count(
    child: pd.Series,
    rng: np.random.Generator,
) -> int:
    """Genera la cantidad diaria de sesiones mediante NB2 zero-truncated."""
    latent_score = calculate_session_latent_score(child)

    # mu_N = exp(alpha_N + kappa_N * L_N)
    mu_n = float(
        np.exp(
            config.SESSION_ALPHA
            + config.SESSION_KAPPA * latent_score
        )
    )

    session_count = sample_negative_binomial_nb2(
        mu=mu_n,
        r=config.SESSION_NB_DISPERSION_R,
        rng=rng,
    )

    # Base v1 supone al menos una sesión por día.
    # Se remuestrea únicamente si aparece cero.
    while (
        config.SESSION_ZERO_TRUNCATED
        and session_count == 0
    ):
        session_count = sample_negative_binomial_nb2(
            mu=mu_n,
            r=config.SESSION_NB_DISPERSION_R,
            rng=rng,
        )

    return session_count


def add_daily_session_count(
    daily_behavior: pd.DataFrame,
    population: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Agrega la cantidad diaria de sesiones N a cada niño-día."""

    # F todavía no estaba incorporada al DataFrame diario.
    result = daily_behavior.merge(
        population[
            [
                "child_id",
                "F",
            ]
        ],
        on="child_id",
        how="left",
        validate="many_to_one",
    )

    session_counts = []

    for _, row in result.iterrows():
        session_counts.append(
            generate_daily_session_count(
                child=row,
                rng=rng,
            )
        )

    result["daily_session_count"] = session_counts

    return result


# ============================================================
# DURACIONES DE SESIONES
# ============================================================

def generate_session_durations(
    total_minutes: float,
    session_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Reparte T entre N sesiones mediante pesos Gamma normalizados."""

    if total_minutes <= 0:
        raise ValueError("total_minutes debe ser mayor que cero.")

    if session_count < 1:
        raise ValueError("session_count debe ser al menos 1.")

    # Cada sesión recibe un peso positivo.
    weights = rng.gamma(
        shape=config.SESSION_DURATION_GAMMA_SHAPE,
        scale=config.SESSION_DURATION_GAMMA_SCALE,
        size=session_count,
    )

    # Normaliza los pesos para que las duraciones sumen exactamente T.
    durations = total_minutes * weights / weights.sum()

    return durations

def build_session_table(
    daily_behavior: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Construye una fila por sesión a partir de T y N de cada niño-día."""

    rows = []

    for _, day in daily_behavior.iterrows():
        total_minutes = float(day["daily_use_minutes"])
        session_count = int(day["daily_session_count"])

        durations = generate_session_durations(
            total_minutes=total_minutes,
            session_count=session_count,
            rng=rng,
        )

        for session_index, duration in enumerate(
            durations,
            start=1,
        ):
            rows.append(
                {
                    "child_id": int(day["child_id"]),
                    "day_index": int(day["day_index"]),
                    "session_index": session_index,
                    "session_duration_minutes": float(duration),
                }
            )

    return pd.DataFrame(rows)

def validate_session_durations(
    daily_behavior: pd.DataFrame,
    sessions: pd.DataFrame,
) -> None:
    """Verifica que las sesiones reproduzcan exactamente T y N."""

    print("\nVALIDACIÓN DE DURACIONES DE SESIÓN\n")

    # Reconstruye T sumando todas las duraciones de cada niño-día.
    reconstructed_time = (
        sessions
        .groupby(["child_id", "day_index"])
        ["session_duration_minutes"]
        .sum()
        .rename("reconstructed_time")
        .reset_index()
    )

    # Reconstruye N contando las sesiones de cada niño-día.
    reconstructed_count = (
        sessions
        .groupby(["child_id", "day_index"])
        .size()
        .rename("reconstructed_count")
        .reset_index()
    )

    validation = (
        daily_behavior[
            [
                "child_id",
                "day_index",
                "daily_use_minutes",
                "daily_session_count",
            ]
        ]
        .merge(
            reconstructed_time,
            on=["child_id", "day_index"],
            validate="one_to_one",
        )
        .merge(
            reconstructed_count,
            on=["child_id", "day_index"],
            validate="one_to_one",
        )
    )

    # Floating point requiere tolerancia numérica.
    assert np.allclose(
        validation["daily_use_minutes"],
        validation["reconstructed_time"],
        rtol=1e-10,
        atol=1e-8,
    )

    assert (
        validation["daily_session_count"]
        == validation["reconstructed_count"]
    ).all()

    assert (sessions["session_duration_minutes"] > 0).all()

    print("Conservación T: OK")
    print("Conservación N: OK")
    print("Duraciones positivas: OK")

    print("\nResumen de duración de sesiones:")
    print(
        sessions["session_duration_minutes"]
        .describe(
            percentiles=[0.05, 0.25, 0.50, 0.75, 0.95]
        )
        .round(2)
    )

    
# ============================================================
# SCHEDULER: VENTANAS TEMPORALES
# ============================================================

def classify_time_segment(
    midpoint: float,
    day: pd.Series,
) -> str:
    """Clasifica un instante del día en una ventana del scheduler."""

    day_start = float(day["day_start_minute"])
    bedtime = float(day["bedtime_minute"])
    previous_bedtime = float(day["previous_bedtime_minute"])

    # Si la noche anterior tuvo bedtime después de medianoche,
    # convertimos esa parte al reloj del día actual.
    previous_bedtime_rollover = (
        previous_bedtime - 24 * 60
        if previous_bedtime > 24 * 60
        else None
    )

    # --------------------------------------------------------
    # CONTINUACIÓN DE LA NOCHE ANTERIOR
    # --------------------------------------------------------

    # Ejemplo:
    # bedtime anterior = 00:20 (+1d)
    # 00:00-00:20 todavía pertenece a pre_bedtime.
    if (
        previous_bedtime_rollover is not None
        and 0 <= midpoint < previous_bedtime_rollover
    ):
        return "pre_bedtime"

    # Desde el bedtime anterior hasta day_start,
    # el uso sigue siendo post-bedtime/overnight.
    if midpoint < day_start:
        return "post_bedtime_overnight"

    # --------------------------------------------------------
    # NOCHE DEL DÍA ACTUAL
    # --------------------------------------------------------

    pre_bedtime_start = (
        bedtime - config.PRE_BEDTIME_WINDOW_MINUTES
    )

    # El bedtime puede quedar después de medianoche (>1440).
    # Dentro del día actual solo clasificamos hasta 24:00.
    if midpoint >= pre_bedtime_start:
        if bedtime > 24 * 60 or midpoint < bedtime:
            return "pre_bedtime"

    if bedtime <= 24 * 60 and midpoint >= bedtime:
        return "post_bedtime_overnight"

    # --------------------------------------------------------
    # HORARIO ESCOLAR
    # --------------------------------------------------------

    if bool(day["has_school_today"]):
        school_start = float(day["school_start_minute"])
        school_end = float(day["school_end_minute"])

        if school_start <= midpoint < school_end:
            return "school"

        # Antes de entrar al colegio se considera morning_free.
        if midpoint < school_start:
            return "morning_free"

        # Después de salir del colegio.
        return "daytime_free"

    # --------------------------------------------------------
    # DÍA SIN COLEGIO
    # --------------------------------------------------------

    morning_end = _clock_to_minutes(
        config.NO_SCHOOL_MORNING_END
    )

    if midpoint < morning_end:
        return "morning_free"

    return "daytime_free"


def get_window_weight(
    window_name: str,
    severity: float,
) -> float:
    """Obtiene el peso del scheduler para una ventana temporal."""

    base_weight = float(
        config.SCHEDULER_WEIGHTS[window_name]
    )

    # Solo el período post-bedtime recibe el efecto débil de S.
    if window_name == "post_bedtime_overnight":
        return float(
            base_weight
            * np.exp(config.BETA_S_NIGHT * severity)
        )

    return base_weight


def build_time_windows(
    day: pd.Series,
    severity: float,
) -> list[TimeWindow]:
    """Particiona las 24 horas en ventanas exclusivas del scheduler."""

    boundaries = {
        0.0,
        float(day["day_start_minute"]),
        float(24 * 60),
    }

    bedtime = float(day["bedtime_minute"])
    previous_bedtime = float(day["previous_bedtime_minute"])

    # Inicio de la ventana pre-bedtime del día actual.
    pre_bedtime_start = (
        bedtime - config.PRE_BEDTIME_WINDOW_MINUTES
    )

    if 0 < pre_bedtime_start < 24 * 60:
        boundaries.add(pre_bedtime_start)

    # Bedtime actual si ocurre antes de medianoche.
    if 0 < bedtime < 24 * 60:
        boundaries.add(bedtime)

    # Continuación después de medianoche del bedtime anterior.
    if previous_bedtime > 24 * 60:
        rollover = previous_bedtime - 24 * 60

        if 0 < rollover < 24 * 60:
            boundaries.add(rollover)

    # Horario escolar.
    if bool(day["has_school_today"]):
        boundaries.add(float(day["school_start_minute"]))
        boundaries.add(float(day["school_end_minute"]))

    # En días sin colegio conservamos una separación
    # operativa entre mañana y resto del día.
    else:
        boundaries.add(
            float(
                _clock_to_minutes(
                    config.NO_SCHOOL_MORNING_END
                )
            )
        )

    sorted_boundaries = sorted(boundaries)

    windows: list[TimeWindow] = []

    for start, end in zip(
        sorted_boundaries[:-1],
        sorted_boundaries[1:],
    ):
        if end <= start:
            continue

        midpoint = (start + end) / 2.0

        window_name = classify_time_segment(
            midpoint=midpoint,
            day=day,
        )

        weight = get_window_weight(
            window_name=window_name,
            severity=severity,
        )

        # Une segmentos adyacentes con la misma etiqueta.
        if (
            windows
            and windows[-1].name == window_name
            and np.isclose(windows[-1].end_minute, start)
        ):
            windows[-1].end_minute = end

        else:
            windows.append(
                TimeWindow(
                    name=window_name,
                    start_minute=start,
                    end_minute=end,
                    weight=weight,
                )
            )

    return windows

# ============================================================
# SCHEDULER: COLOCACIÓN DE SESIONES
# ============================================================

def get_free_gaps(
    occupied_intervals: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Calcula los intervalos libres restantes dentro de las 24 horas."""

    if not occupied_intervals:
        return [(0.0, float(24 * 60))]

    intervals = sorted(occupied_intervals)

    gaps = []
    current = 0.0

    for start, end in intervals:
        if start > current:
            gaps.append((current, start))

        current = max(current, end)

    if current < 24 * 60:
        gaps.append((current, float(24 * 60)))

    return gaps


def build_feasible_start_segments(
    duration: float,
    windows: list[TimeWindow],
    occupied_intervals: list[tuple[float, float]],
) -> list[dict]:
    """Obtiene intervalos donde una sesión puede comenzar sin solaparse."""

    free_gaps = get_free_gaps(occupied_intervals)

    candidates = []

    for gap_start, gap_end in free_gaps:

        # Último instante posible de inicio para que la sesión
        # termine antes de cerrar el gap.
        latest_start = gap_end - duration

        if latest_start < gap_start:
            continue

        for window in windows:

            # El inicio debe caer dentro de la ventana.
            start = max(
                gap_start,
                window.start_minute,
            )

            end = min(
                latest_start,
                window.end_minute,
            )

            if end <= start:
                continue

            available_start_range = end - start

            # Probabilidad proporcional a:
            # intensidad de la ventana × cantidad de inicios posibles.
            mass = (
                window.weight
                * available_start_range
            )

            if mass <= 0:
                continue

            candidates.append(
                {
                    "start": float(start),
                    "end": float(end),
                    "weight": float(window.weight),
                    "mass": float(mass),
                    "window_name": window.name,
                }
            )

    return candidates


def sample_session_start(
    duration: float,
    windows: list[TimeWindow],
    occupied_intervals: list[tuple[float, float]],
    rng: np.random.Generator,
) -> tuple[float, str] | None:
    """Muestrea un inicio válido ponderado por intensidad y espacio libre."""

    candidates = build_feasible_start_segments(
        duration=duration,
        windows=windows,
        occupied_intervals=occupied_intervals,
    )

    if not candidates:
        return None

    masses = np.array(
        [candidate["mass"] for candidate in candidates],
        dtype=float,
    )

    probabilities = masses / masses.sum()

    candidate_index = int(
        rng.choice(
            len(candidates),
            p=probabilities,
        )
    )

    candidate = candidates[candidate_index]

    start = float(
        rng.uniform(
            candidate["start"],
            candidate["end"],
        )
    )

    return start, candidate["window_name"]


def schedule_day_sessions_once(
    day_sessions: pd.DataFrame,
    day: pd.Series,
    severity: float,
    rng: np.random.Generator,
) -> pd.DataFrame | None:
    """Intenta colocar todas las sesiones de un día sin solapamientos."""

    windows = build_time_windows(
        day=day,
        severity=severity,
    )

    validate_time_windows(windows)

    # Colocar las sesiones largas primero reduce la posibilidad
    # de fragmentar el espacio disponible innecesariamente.
    ordered_sessions = (
        day_sessions
        .sort_values(
            "session_duration_minutes",
            ascending=False,
        )
        .copy()
    )

    occupied_intervals: list[tuple[float, float]] = []

    scheduled_rows = []

    for _, session in ordered_sessions.iterrows():

        duration = float(
            session["session_duration_minutes"]
        )

        sampled = sample_session_start(
            duration=duration,
            windows=windows,
            occupied_intervals=occupied_intervals,
            rng=rng,
        )

        if sampled is None:
            return None

        start, start_window = sampled

        end = start + duration

        # Base v1 no permite que una sesión sintética
        # atraviese medianoche.
        if end > 24 * 60:
            return None

        occupied_intervals.append(
            (start, end)
        )

        scheduled_rows.append(
            {
                "child_id": int(session["child_id"]),
                "day_index": int(session["day_index"]),
                "session_index": int(session["session_index"]),
                "session_duration_minutes": duration,
                "session_start_minute": float(start),
                "session_end_minute": float(end),

                # Ventana donde COMIENZA la sesión.
                # La sesión puede después atravesar otras ventanas.
                "session_start_window": start_window,
            }
        )

    return pd.DataFrame(scheduled_rows)


def schedule_day_sessions(
    day_sessions: pd.DataFrame,
    day: pd.Series,
    severity: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Reintenta el scheduling completo del día hasta encontrar solución."""

    for attempt in range(1, config.SCHEDULER_MAX_DAY_RETRIES + 1):

        scheduled = schedule_day_sessions_once(
            day_sessions=day_sessions,
            day=day,
            severity=severity,
            rng=rng,
        )

        if scheduled is not None:
            # Guarda cuántos intentos necesitó el niño-día.
            # Es metadata de diagnóstico y nunca será una feature.
            scheduled["scheduler_attempts"] = attempt

            return (
                scheduled
                .sort_values("session_index")
                .reset_index(drop=True)
            )

    raise RuntimeError(
        "No fue posible calendarizar todas las sesiones "
        f"del child_id={int(day['child_id'])}, "
        f"day_index={int(day['day_index'])} "
        f"después de {config.SCHEDULER_MAX_DAY_RETRIES} intentos."
    )

def schedule_all_sessions(
    sessions: pd.DataFrame,
    daily_behavior: pd.DataFrame,
    rng: np.random.Generator,
    show_progress: bool = False,
) -> pd.DataFrame:
    """Calendariza todas las sesiones de todos los niño-día."""

    scheduled_days = []

    total_days = len(daily_behavior)

    # Actualiza la barra aproximadamente 20 veces.
    progress_step = max(1, total_days // 20)

    for position, (_, day) in enumerate(
        daily_behavior.iterrows(),
        start=1,
    ):

        child_id = int(day["child_id"])
        day_index = int(day["day_index"])

        day_sessions = sessions.loc[
            (sessions["child_id"] == child_id)
            & (sessions["day_index"] == day_index)
        ]

        severity = float(day["S"])

        scheduled = schedule_day_sessions(
            day_sessions=day_sessions,
            day=day,
            severity=severity,
            rng=rng,
        )

        scheduled_days.append(scheduled)

        # Muestra progreso sin llenar la terminal de mensajes.
        if (
            show_progress
            and (
                position % progress_step == 0
                or position == total_days
            )
        ):
            fraction = position / total_days
            bar_length = 20
            filled = int(fraction * bar_length)

            bar = (
                "█" * filled
                + "░" * (bar_length - filled)
            )

            print(
                f"\rScheduler [{bar}] "
                f"{fraction * 100:5.1f}%",
                end="",
                flush=True,
            )

    if show_progress:
        print()

    return pd.concat(
        scheduled_days,
        ignore_index=True,
    )

# ============================================================
# OVERLAPS CONTEXTUALES
# ============================================================

def calculate_interval_overlap(
    start_a: float,
    end_a: float,
    start_b: float,
    end_b: float,
) -> float:
    """Calcula los minutos de intersección entre dos intervalos."""
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)

    return max(0.0, overlap_end - overlap_start)

def calculate_overlap_with_window_type(
    session_start: float,
    session_end: float,
    windows: list[TimeWindow],
    window_name: str,
) -> float:
    """Suma el overlap de una sesión con todas las ventanas de un tipo."""

    overlap_minutes = 0.0

    for window in windows:
        if window.name != window_name:
            continue

        overlap_minutes += calculate_interval_overlap(
            start_a=session_start,
            end_a=session_end,
            start_b=window.start_minute,
            end_b=window.end_minute,
        )

    return overlap_minutes

def add_contextual_overlaps(
    scheduled_sessions: pd.DataFrame,
    daily_behavior: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega minutos escolares y post-bedtime a cada sesión."""

    result_groups = []

    # Permite encontrar rápidamente el contexto de cada niño-día.
    day_lookup = daily_behavior.set_index(
        ["child_id", "day_index"]
    )

    for (child_id, day_index), group in scheduled_sessions.groupby(
        ["child_id", "day_index"],
        sort=False,
    ):
        day = day_lookup.loc[
            (child_id, day_index)
        ]

        severity = float(day["S"])

        # Reutiliza exactamente la misma partición temporal
        # utilizada por el scheduler.
        windows = build_time_windows(
            day=day,
            severity=severity,
        )

        group = group.copy()

        school_minutes = []
        post_bedtime_minutes = []

        for _, session in group.iterrows():
            start = float(
                session["session_start_minute"]
            )

            end = float(
                session["session_end_minute"]
            )

            school_minutes.append(
                calculate_overlap_with_window_type(
                    session_start=start,
                    session_end=end,
                    windows=windows,
                    window_name="school",
                )
            )

            post_bedtime_minutes.append(
                calculate_overlap_with_window_type(
                    session_start=start,
                    session_end=end,
                    windows=windows,
                    window_name="post_bedtime_overnight",
                )
            )

        group["school_use_minutes"] = school_minutes
        group["post_bedtime_use_minutes"] = post_bedtime_minutes

        result_groups.append(group)

    return pd.concat(
        result_groups,
        ignore_index=True,
    )

# ============================================================
# EPISODIOS DE APLICACIONES / FOREGROUND
# ============================================================

def calculate_app_episode_rate(fragmentation: float) -> float:
    """Calcula la tasa de episodios adicionales según F."""

    # rho_i = exp(alpha_M + kappa_F * F_i)
    return float(
        np.exp(
            config.APP_EPISODE_ALPHA
            + config.APP_EPISODE_KAPPA_F * fragmentation
        )
    )


def generate_episode_count(
    session_duration: float,
    fragmentation: float,
    rng: np.random.Generator,
) -> int:
    """Genera la cantidad de episodios de foreground de una sesión."""

    if session_duration <= 0:
        raise ValueError(
            "session_duration debe ser mayor que cero."
        )

    rho = calculate_app_episode_rate(
        fragmentation=fragmentation,
    )

    # M_s = 1 + Poisson(D_s * rho_i)
    additional_episodes = int(
        rng.poisson(
            session_duration * rho
        )
    )

    return (
        config.APP_EPISODE_MIN_COUNT
        + additional_episodes
    )


def generate_episode_durations(
    session_duration: float,
    episode_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Reparte la duración de una sesión entre sus episodios."""

    if episode_count < 1:
        raise ValueError(
            "episode_count debe ser al menos 1."
        )

    # Genera pesos positivos para los episodios.
    weights = rng.gamma(
        shape=config.APP_EPISODE_GAMMA_SHAPE,
        scale=config.APP_EPISODE_GAMMA_SCALE,
        size=episode_count,
    )

    # Conserva exactamente la duración total de la sesión.
    durations = (
        session_duration
        * weights
        / weights.sum()
    )

    return durations


def build_app_episode_table(
    scheduled_sessions: pd.DataFrame,
    daily_behavior: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Construye los episodios de foreground dentro de cada sesión."""

    # F es estable a nivel niño. Se obtiene una única fila
    # por child_id para evitar duplicar sesiones en el merge.
    child_fragmentation = (
        daily_behavior[
            [
                "child_id",
                "F",
            ]
        ]
        .drop_duplicates(subset=["child_id"])
    )

    sessions_with_f = scheduled_sessions.merge(
        child_fragmentation,
        on="child_id",
        how="left",
        validate="many_to_one",
    )

    rows = []

    for _, session in sessions_with_f.iterrows():

        session_duration = float(
            session["session_duration_minutes"]
        )

        fragmentation = float(
            session["F"]
        )

        episode_count = generate_episode_count(
            session_duration=session_duration,
            fragmentation=fragmentation,
            rng=rng,
        )

        episode_durations = generate_episode_durations(
            session_duration=session_duration,
            episode_count=episode_count,
            rng=rng,
        )

        # Los episodios ocupan secuencialmente toda la sesión.
        current_start = float(
            session["session_start_minute"]
        )

        for episode_index, duration in enumerate(
            episode_durations,
            start=1,
        ):
            episode_start = current_start
            episode_end = episode_start + float(duration)

            rows.append(
                {
                    "child_id": int(session["child_id"]),
                    "day_index": int(session["day_index"]),
                    "session_index": int(
                        session["session_index"]
                    ),
                    "episode_index": episode_index,
                    "episode_duration_minutes": float(
                        duration
                    ),
                    "episode_start_minute": float(
                        episode_start
                    ),
                    "episode_end_minute": float(
                        episode_end
                    ),
                }
            )

            current_start = episode_end

    return pd.DataFrame(rows)

# ============================================================
# PREFERENCIAS Y CATEGORÍAS DE APLICACIONES
# ============================================================

def generate_child_category_preferences(
    daily_behavior: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Genera un vector de preferencias de categorías para cada niño."""

    child_ids = (
        daily_behavior["child_id"]
        .drop_duplicates()
        .sort_values()
        .to_numpy()
    )

    alpha = np.asarray(
        config.CATEGORY_DIRICHLET_ALPHA,
        dtype=float,
    )

    if len(alpha) != len(config.APP_CATEGORIES):
        raise ValueError(
            "CATEGORY_DIRICHLET_ALPHA debe tener un valor "
            "por cada categoría de aplicación."
        )

    # Cada fila es un vector de probabilidades que suma 1.
    preferences = rng.dirichlet(
        alpha=alpha,
        size=len(child_ids),
    )

    data = {
        "child_id": child_ids.astype(int),
    }

    for category_index, category in enumerate(
        config.APP_CATEGORIES
    ):
        data[f"category_prob_{category}"] = (
            preferences[:, category_index]
        )

    return pd.DataFrame(data)


def assign_episode_categories(
    app_episodes: pd.DataFrame,
    category_preferences: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Asigna una categoría a cada episodio según la preferencia del niño."""

    result = app_episodes.copy()

    probability_columns = [
        f"category_prob_{category}"
        for category in config.APP_CATEGORIES
    ]

    preference_lookup = (
        category_preferences
        .set_index("child_id")
    )

    episode_categories = pd.Series(
        index=result.index,
        dtype="object",
    )

    # Todos los episodios de un mismo niño comparten
    # el mismo vector individual de preferencias.
    for child_id, indices in result.groupby(
        "child_id",
        sort=False,
    ).groups.items():

        probabilities = (
            preference_lookup
            .loc[child_id, probability_columns]
            .to_numpy(dtype=float)
        )

        sampled_categories = rng.choice(
            config.APP_CATEGORIES,
            size=len(indices),
            p=probabilities,
        )

        episode_categories.loc[indices] = (
            sampled_categories
        )

    result["app_category"] = episode_categories

    return result

def validate_app_episodes(
    scheduled_sessions: pd.DataFrame,
    app_episodes: pd.DataFrame,
) -> None:
    """Verifica cantidad, duración y límites de los episodios."""

    print("\nVALIDACIÓN DE EPISODIOS DE APPS\n")

    # Todo episodio debe tener duración positiva.
    assert (
        app_episodes["episode_duration_minutes"] > 0
    ).all()

    assert (
        app_episodes["episode_end_minute"]
        > app_episodes["episode_start_minute"]
    ).all()

    # Cada sesión debe tener al menos un episodio.
    reconstructed_count = (
        app_episodes
        .groupby(
            [
                "child_id",
                "day_index",
                "session_index",
            ]
        )
        .size()
        .rename("episode_count")
        .reset_index()
    )

    assert (
        reconstructed_count["episode_count"]
        >= config.APP_EPISODE_MIN_COUNT
    ).all()

    # Reconstruye duración de sesión sumando episodios.
    reconstructed_duration = (
        app_episodes
        .groupby(
            [
                "child_id",
                "day_index",
                "session_index",
            ]
        )["episode_duration_minutes"]
        .sum()
        .rename("reconstructed_session_duration")
        .reset_index()
    )

    validation = (
        scheduled_sessions[
            [
                "child_id",
                "day_index",
                "session_index",
                "session_duration_minutes",
                "session_start_minute",
                "session_end_minute",
            ]
        ]
        .merge(
            reconstructed_duration,
            on=[
                "child_id",
                "day_index",
                "session_index",
            ],
            validate="one_to_one",
        )
        .merge(
            reconstructed_count,
            on=[
                "child_id",
                "day_index",
                "session_index",
            ],
            validate="one_to_one",
        )
    )

    assert np.allclose(
        validation["session_duration_minutes"],
        validation[
            "reconstructed_session_duration"
        ],
        rtol=1e-10,
        atol=1e-8,
    )

    # Primer y último episodio deben coincidir
    # con los límites de cada sesión.
    episode_bounds = (
        app_episodes
        .groupby(
            [
                "child_id",
                "day_index",
                "session_index",
            ]
        )
        .agg(
            first_episode_start=(
                "episode_start_minute",
                "min",
            ),
            last_episode_end=(
                "episode_end_minute",
                "max",
            ),
        )
        .reset_index()
    )

    validation = validation.merge(
        episode_bounds,
        on=[
            "child_id",
            "day_index",
            "session_index",
        ],
        validate="one_to_one",
    )

    assert np.allclose(
        validation["session_start_minute"],
        validation["first_episode_start"],
        rtol=1e-10,
        atol=1e-8,
    )

    assert np.allclose(
        validation["session_end_minute"],
        validation["last_episode_end"],
        rtol=1e-10,
        atol=1e-8,
    )

    print("Episodios positivos: OK")
    print("Al menos 1 episodio por sesión: OK")
    print("Conservación de duración de sesión: OK")
    print("Límites temporales sesión-episodios: OK")

    print("\nResumen de episodios por sesión:")

    print(
        reconstructed_count["episode_count"]
        .describe(
            percentiles=[
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
            ]
        )
        .round(2)
    )

    print("\nResumen de duración de episodios:")

    print(
        app_episodes["episode_duration_minutes"]
        .describe(
            percentiles=[
                0.05,
                0.50,
                0.95,
                0.99,
            ]
        )
        .round(2)
    )

def diagnose_app_episodes(
    scheduled_sessions: pd.DataFrame,
    app_episodes: pd.DataFrame,
) -> None:
    """Diagnostica episodios extremadamente cortos y sesiones fragmentadas."""

    print("\nDIAGNÓSTICO DE EPISODIOS DE APPS\n")

    durations = app_episodes["episode_duration_minutes"]

    print("Duración mínima exacta (min):")
    print(f"{durations.min():.8f}")

    print("\nEpisodios menores a 1 segundo:")
    under_1s = (durations < (1 / 60)).sum()
    print(
        f"{under_1s} "
        f"({under_1s / len(durations):.4%})"
    )

    print("\nEpisodios menores a 5 segundos:")
    under_5s = (durations < (5 / 60)).sum()
    print(
        f"{under_5s} "
        f"({under_5s / len(durations):.4%})"
    )

    print("\nEpisodios menores a 10 segundos:")
    under_10s = (durations < (10 / 60)).sum()
    print(
        f"{under_10s} "
        f"({under_10s / len(durations):.4%})"
    )

    # Evalúa cuánto tiempo total representan los episodios muy cortos.
    total_episode_minutes = durations.sum()

    under_1s_minutes = durations[
        durations < (1 / 60)
    ].sum()

    under_5s_minutes = durations[
        durations < (5 / 60)
    ].sum()

    under_10s_minutes = durations[
        durations < (10 / 60)
    ].sum()

    print("\nPorcentaje del TIEMPO total en episodios < 1 segundo:")
    print(
        f"{under_1s_minutes / total_episode_minutes:.6%}"
    )

    print("\nPorcentaje del TIEMPO total en episodios < 5 segundos:")
    print(
        f"{under_5s_minutes / total_episode_minutes:.6%}"
    )

    print("\nPorcentaje del TIEMPO total en episodios < 10 segundos:")
    print(
        f"{under_10s_minutes / total_episode_minutes:.6%}"
    )

    episode_counts = (
        app_episodes
        .groupby(
            [
                "child_id",
                "day_index",
                "session_index",
            ]
        )
        .size()
        .rename("episode_count")
        .reset_index()
    )

    diagnostic = scheduled_sessions[
        [
            "child_id",
            "day_index",
            "session_index",
            "session_duration_minutes",
        ]
    ].merge(
        episode_counts,
        on=[
            "child_id",
            "day_index",
            "session_index",
        ],
        validate="one_to_one",
    )

    print("\nSesiones con más de 20 episodios:")
    over_20 = (diagnostic["episode_count"] > 20).sum()

    print(
        f"{over_20} "
        f"({over_20 / len(diagnostic):.4%})"
    )

    print("\n10 sesiones con mayor cantidad de episodios:")

    print(
        diagnostic
        .sort_values(
            "episode_count",
            ascending=False,
        )
        .head(10)
        .to_string(index=False)
    )

def validate_app_categories(
    app_episodes: pd.DataFrame,
    category_preferences: pd.DataFrame,
) -> None:
    """Verifica preferencias y asignaciones de categorías."""

    print("\nVALIDACIÓN DE CATEGORÍAS DE APPS\n")

    probability_columns = [
        f"category_prob_{category}"
        for category in config.APP_CATEGORIES
    ]

    probabilities = category_preferences[
        probability_columns
    ]

    # Cada vector individual debe ser una distribución válida.
    assert (probabilities > 0).all().all()

    assert np.allclose(
        probabilities.sum(axis=1),
        1.0,
        rtol=1e-10,
        atol=1e-10,
    )

    # Todo episodio debe recibir exactamente una categoría válida.
    assert app_episodes["app_category"].notna().all()

    assert set(
        app_episodes["app_category"].unique()
    ).issubset(
        set(config.APP_CATEGORIES)
    )

    print("Preferencias positivas: OK")
    print("Preferencias suman 1 por niño: OK")
    print("Todos los episodios tienen categoría válida: OK")

    print("\nPreferencia media generada por categoría:")

    mean_preferences = (
        probabilities
        .mean()
        .rename(
            lambda column: column.replace(
                "category_prob_",
                "",
            )
        )
        .round(4)
    )

    print(mean_preferences)

    print("\nShare poblacional REAL de minutos por categoría:")

    category_minutes = (
        app_episodes
        .groupby("app_category")
        ["episode_duration_minutes"]
        .sum()
    )

    category_shares = (
        category_minutes
        / category_minutes.sum()
    )

    print(
        category_shares
        .reindex(config.APP_CATEGORIES)
        .round(4)
    )

def diagnose_app_category_relationships(
    app_episodes: pd.DataFrame,
    daily_behavior: pd.DataFrame,
) -> None:
    """Comprueba que S y edad no determinen artificialmente las categorías."""

    print("\nDIAGNÓSTICO DE RELACIONES DE CATEGORÍAS\n")

    child_category_minutes = (
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

    total_minutes = child_category_minutes.sum(
        axis=1
    )

    child_category_shares = (
        child_category_minutes
        .div(total_minutes, axis=0)
    )

    child_context = (
        daily_behavior[
            [
                "child_id",
                "S",
                "age_scaled",
            ]
        ]
        .drop_duplicates(subset=["child_id"])
        .set_index("child_id")
    )

    diagnostic = child_context.join(
        child_category_shares,
        how="inner",
    )

    print("Correlaciones de shares con S:")

    print(
        diagnostic[
            ["S", *config.APP_CATEGORIES]
        ]
        .corr()["S"]
        .drop("S")
        .round(3)
    )

    print("\nCorrelaciones de shares con age_scaled:")

    print(
        diagnostic[
            [
                "age_scaled",
                *config.APP_CATEGORIES,
            ]
        ]
        .corr()["age_scaled"]
        .drop("age_scaled")
        .round(3)
    )

def validate_contextual_overlaps(
    daily_behavior: pd.DataFrame,
    scheduled_sessions: pd.DataFrame,
) -> None:
    """Verifica la consistencia de minutos escolares y post-bedtime."""

    print("\nVALIDACIÓN DE OVERLAPS CONTEXTUALES\n")

    # Ningún overlap puede ser negativo.
    assert (
        scheduled_sessions["school_use_minutes"] >= 0
    ).all()

    assert (
        scheduled_sessions["post_bedtime_use_minutes"] >= 0
    ).all()

    # Ningún overlap puede superar la duración de su sesión.
    assert (
        scheduled_sessions["school_use_minutes"]
        <= scheduled_sessions["session_duration_minutes"] + 1e-9
    ).all()

    assert (
        scheduled_sessions["post_bedtime_use_minutes"]
        <= scheduled_sessions["session_duration_minutes"] + 1e-9
    ).all()

    daily_context = (
        scheduled_sessions
        .groupby(["child_id", "day_index"])
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

    validation = daily_behavior[
        [
            "child_id",
            "day_index",
            "has_school_today",
            "daily_use_minutes",
        ]
    ].merge(
        daily_context,
        on=["child_id", "day_index"],
        validate="one_to_one",
    )

    # El uso contextual nunca puede superar T.
    assert (
        validation["school_use_minutes"]
        <= validation["daily_use_minutes"] + 1e-8
    ).all()

    assert (
        validation["post_bedtime_use_minutes"]
        <= validation["daily_use_minutes"] + 1e-8
    ).all()

    # En días sin colegio, school_use debe ser exactamente cero.
    no_school = ~validation["has_school_today"]

    assert np.allclose(
        validation.loc[
            no_school,
            "school_use_minutes",
        ],
        0.0,
        atol=1e-10,
    )

    print("Overlaps no negativos: OK")
    print("Overlap <= duración de sesión: OK")
    print("Uso contextual <= T: OK")
    print("School use = 0 en días sin colegio: OK")

    # Ratios diarios SOLO para diagnóstico.
    validation["school_use_ratio"] = (
        validation["school_use_minutes"]
        / validation["daily_use_minutes"]
    )

    validation["post_bedtime_use_ratio"] = (
        validation["post_bedtime_use_minutes"]
        / validation["daily_use_minutes"]
    )

    print("\nResumen diario school_use_ratio:")
    print(
        validation["school_use_ratio"]
        .describe(
            percentiles=[0.50, 0.90, 0.95, 0.99]
        )
        .round(4)
    )

    print("\nResumen diario post_bedtime_use_ratio:")
    print(
        validation["post_bedtime_use_ratio"]
        .describe(
            percentiles=[0.50, 0.90, 0.95, 0.99]
        )
        .round(4)
    )

def diagnose_contextual_overlaps(
    daily_behavior: pd.DataFrame,
    scheduled_sessions: pd.DataFrame,
) -> None:
    """Diagnostica extremos y relaciones latentes de los overlaps."""

    print("\nDIAGNÓSTICO DE OVERLAPS CONTEXTUALES\n")

    daily_context = (
        scheduled_sessions
        .groupby(["child_id", "day_index"])
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

    diagnostic = daily_behavior[
        [
            "child_id",
            "day_index",
            "daily_use_minutes",
            "S",
        ]
    ].merge(
        daily_context,
        on=["child_id", "day_index"],
        validate="one_to_one",
    )

    diagnostic["school_use_ratio"] = (
        diagnostic["school_use_minutes"]
        / diagnostic["daily_use_minutes"]
    )

    diagnostic["post_bedtime_use_ratio"] = (
        diagnostic["post_bedtime_use_minutes"]
        / diagnostic["daily_use_minutes"]
    )

    total_days = len(diagnostic)

    # --------------------------------------------------------
    # EXTREMOS
    # --------------------------------------------------------

    post_equal_one = np.isclose(
        diagnostic["post_bedtime_use_ratio"],
        1.0,
        atol=1e-10,
    ).sum()

    post_over_half = (
        diagnostic["post_bedtime_use_ratio"] > 0.50
    ).sum()

    school_over_half = (
        diagnostic["school_use_ratio"] > 0.50
    ).sum()

    print(
        "Días con post_bedtime_use_ratio = 1: "
        f"{post_equal_one} "
        f"({post_equal_one / total_days:.4%})"
    )

    print(
        "Días con post_bedtime_use_ratio > 0.50: "
        f"{post_over_half} "
        f"({post_over_half / total_days:.4%})"
    )

    print(
        "Días con school_use_ratio > 0.50: "
        f"{school_over_half} "
        f"({school_over_half / total_days:.4%})"
    )

    # --------------------------------------------------------
    # RELACIONES CON S
    # --------------------------------------------------------

    print("\nCorrelaciones con S:")

    correlations = diagnostic[
        [
            "S",
            "school_use_ratio",
            "post_bedtime_use_ratio",
        ]
    ].corr()["S"].round(3)

    print(correlations)

def validate_scheduler_statistics(
    scheduled_sessions: pd.DataFrame,
) -> None:
    """Muestra diagnósticos estadísticos del scheduler a gran escala."""

    print("\nVALIDACIÓN ESTADÍSTICA DEL SCHEDULER\n")

    # Un valor por niño-día.
    attempts = (
        scheduled_sessions
        .groupby(["child_id", "day_index"])
        ["scheduler_attempts"]
        .first()
    )

    print("Intentos necesarios por niño-día:")
    print(
        attempts
        .describe(
            percentiles=[0.50, 0.90, 0.95, 0.99]
        )
        .round(2)
    )

    print("\nProporción de sesiones por ventana de inicio:")
    print(
        scheduled_sessions["session_start_window"]
        .value_counts(normalize=True)
        .sort_index()
        .round(4)
    )

    print("\nDuración media por ventana de inicio:")
    print(
        scheduled_sessions
        .groupby("session_start_window")
        ["session_duration_minutes"]
        .mean()
        .sort_index()
        .round(2)
    )

    print("\nDuración mediana por ventana de inicio:")
    print(
        scheduled_sessions
        .groupby("session_start_window")
        ["session_duration_minutes"]
        .median()
        .sort_index()
        .round(2)
    )

def validate_time_windows(
    windows: list[TimeWindow],
) -> None:
    """Verifica cobertura completa, orden y ausencia de solapamientos."""

    assert len(windows) > 0

    # El scheduler debe cubrir exactamente todo el día calendario.
    assert np.isclose(windows[0].start_minute, 0.0)
    assert np.isclose(
        windows[-1].end_minute,
        24 * 60,
    )

    total_duration = 0.0

    for index, window in enumerate(windows):
        assert window.duration_minutes > 0
        assert window.weight > 0

        total_duration += window.duration_minutes

        if index > 0:
            previous = windows[index - 1]

            # Sin huecos ni solapamientos.
            assert np.isclose(
                previous.end_minute,
                window.start_minute,
            )

    assert np.isclose(
        total_duration,
        24 * 60,
    )


def validate_scheduled_sessions(
    daily_behavior: pd.DataFrame,
    scheduled_sessions: pd.DataFrame,
) -> None:
    """Verifica conservación, límites diarios y ausencia de solapamientos."""

    print("\nVALIDACIÓN DEL SCHEDULER\n")

    # Todas las sesiones deben permanecer dentro del día.
    assert (
        scheduled_sessions["session_start_minute"] >= 0
    ).all()

    assert (
        scheduled_sessions["session_end_minute"]
        <= 24 * 60
    ).all()

    assert (
        scheduled_sessions["session_end_minute"]
        > scheduled_sessions["session_start_minute"]
    ).all()

    # Comprueba ausencia de solapamientos niño-día por niño-día.
    for (_, _), group in scheduled_sessions.groupby(
        ["child_id", "day_index"]
    ):

        ordered = group.sort_values(
            "session_start_minute"
        )

        previous_end = None

        for _, session in ordered.iterrows():

            start = float(
                session["session_start_minute"]
            )

            end = float(
                session["session_end_minute"]
            )

            if previous_end is not None:
                assert start >= previous_end - 1e-9

            previous_end = end

    # Reconstruye T desde las sesiones ya calendarizadas.
    reconstructed = (
        scheduled_sessions
        .groupby(["child_id", "day_index"])
        ["session_duration_minutes"]
        .sum()
        .rename("scheduled_time")
        .reset_index()
    )

    check = daily_behavior[
        [
            "child_id",
            "day_index",
            "daily_use_minutes",
        ]
    ].merge(
        reconstructed,
        on=["child_id", "day_index"],
        validate="one_to_one",
    )

    assert np.allclose(
        check["daily_use_minutes"],
        check["scheduled_time"],
        rtol=1e-10,
        atol=1e-8,
    )

    print("Sesiones dentro del día: OK")
    print("Ausencia de solapamientos: OK")
    print("Conservación de T después del scheduling: OK")


def print_time_windows(
    windows: list[TimeWindow],
) -> None:
    """Muestra las ventanas del scheduler de forma legible."""

    print("\nVENTANAS DEL SCHEDULER\n")

    for window in windows:
        print(
            f"{window.name:28s} "
            f"{minutes_to_clock(window.start_minute):12s} -> "
            f"{minutes_to_clock(window.end_minute):12s} "
            f"| duración={window.duration_minutes:7.1f} min "
            f"| peso={window.weight:.3f}"
        )


# ============================================================
# DEBUG
# ============================================================

def main() -> None:
    """Genera una semana de contexto para un niño de prueba."""

    # Import local para evitar dependencia circular entre módulos.
    from generate_population import generate_population

    # Crea substreams aleatorios independientes y reproducibles.
    seed_sequence = np.random.SeedSequence(config.CALIBRATION_SEED)
    (
        population_seed,
        context_seed,
        time_seed,
        session_seed,
        duration_seed,
        scheduler_seed,
        episode_seed,
        category_seed,
    ) = seed_sequence.spawn(8)

    population = generate_population(
        n_children=1,
        seed=population_seed,
    )

    contexts = generate_daily_contexts(
        population=population,
        seed=context_seed,
        n_days=config.N_DAYS,
    )

    validate_daily_contexts(contexts)

    # Usa un substream separado para la generación del tiempo diario.
    time_rng = np.random.default_rng(time_seed)

    daily_behavior = add_daily_use_time(
        contexts=contexts,
        population=population,
        rng=time_rng,
    )

    # Usa un substream independiente para la cantidad de sesiones.
    session_rng = np.random.default_rng(session_seed)

    daily_behavior = add_daily_session_count(
        daily_behavior=daily_behavior,
        population=population,
        rng=session_rng,
    )

    assert (daily_behavior["daily_use_minutes"] > 0).all()
    assert (
        daily_behavior["daily_use_minutes"]
        < config.MAX_DAILY_MINUTES
    ).all()

    assert (daily_behavior["daily_session_count"] >= 1).all()

    print("\nInvariantes de tiempo diario: OK")
    print("\nInvariantes de sesiones diarias: OK")

    # Usa un substream independiente para repartir T entre sesiones.
    duration_rng = np.random.default_rng(duration_seed)

    sessions = build_session_table(
        daily_behavior=daily_behavior,
        rng=duration_rng,
    )

    validate_session_durations(
        daily_behavior=daily_behavior,
        sessions=sessions,
    )

    # Usa un substream independiente para calendarizar las sesiones.
    scheduler_rng = np.random.default_rng(
        scheduler_seed
    )

    scheduled_sessions = schedule_all_sessions(
        sessions=sessions,
        daily_behavior=daily_behavior,
        rng=scheduler_rng,
    )

    validate_scheduled_sessions(
        daily_behavior=daily_behavior,
        scheduled_sessions=scheduled_sessions,
    )

    # Calcula los minutos reales que cada sesión aporta
    # a horario escolar y post-bedtime.
    scheduled_sessions = add_contextual_overlaps(
        scheduled_sessions=scheduled_sessions,
        daily_behavior=daily_behavior,
    )

    # Usa un substream independiente para generar
    # episodios de foreground dentro de cada sesión.
    episode_rng = np.random.default_rng(
        episode_seed
    )

    app_episodes = build_app_episode_table(
        scheduled_sessions=scheduled_sessions,
        daily_behavior=daily_behavior,
        rng=episode_rng,
    )

    validate_app_episodes(
        scheduled_sessions=scheduled_sessions,
        app_episodes=app_episodes,
    )

    # Usa un substream independiente para las preferencias
    # individuales y categorías de aplicaciones.
    category_rng = np.random.default_rng(
        category_seed
    )

    category_preferences = (
        generate_child_category_preferences(
            daily_behavior=daily_behavior,
            rng=category_rng,
        )
    )

    app_episodes = assign_episode_categories(
        app_episodes=app_episodes,
        category_preferences=category_preferences,
        rng=category_rng,
    )

    validate_app_categories(
        app_episodes=app_episodes,
        category_preferences=category_preferences,
    )

    print("\nEPISODIOS DE APPS - PRIMERAS 30 FILAS\n")

    debug_episodes = app_episodes.head(30).copy()

    debug_episodes["start"] = (
        debug_episodes["episode_start_minute"]
        .apply(minutes_to_clock)
    )

    debug_episodes["end"] = (
        debug_episodes["episode_end_minute"]
        .apply(minutes_to_clock)
    )

    debug_episodes["duration"] = (
        debug_episodes["episode_duration_minutes"]
        .round(2)
    )

    print(
        debug_episodes[
            [
                "day_index",
                "session_index",
                "episode_index",
                "start",
                "end",
                "duration",
                "app_category",
            ]
        ]
        .to_string(index=False)
    )

    print("\nSESIONES CALENDARIZADAS - DÍA 0\n")

    # Toma las sesiones del día 0 después de haber calculado
    # los overlaps con horario escolar y post-bedtime.
    debug_scheduled = scheduled_sessions.loc[
        scheduled_sessions["day_index"] == 0
    ].copy()

    # Convierte los minutos a horarios legibles.
    debug_scheduled["start"] = (
        debug_scheduled["session_start_minute"]
        .apply(minutes_to_clock)
    )

    debug_scheduled["end"] = (
        debug_scheduled["session_end_minute"]
        .apply(minutes_to_clock)
    )

    # Redondea únicamente para mostrar los resultados.
    debug_scheduled["duration"] = (
        debug_scheduled["session_duration_minutes"]
        .round(2)
    )

    debug_scheduled["school_use_minutes"] = (
        debug_scheduled["school_use_minutes"]
        .round(2)
    )

    debug_scheduled["post_bedtime_use_minutes"] = (
        debug_scheduled["post_bedtime_use_minutes"]
        .round(2)
    )

    # Ordena las sesiones cronológicamente.
    debug_scheduled = debug_scheduled.sort_values(
        "session_start_minute"
    )

    print(
        debug_scheduled[
            [
                "session_index",
                "start",
                "end",
                "duration",
                "session_start_window",
                "school_use_minutes",
                "post_bedtime_use_minutes",
            ]
        ]
        .to_string(index=False)
    )

    debug_columns = [
        "child_id",
        "day_index",
        "weekday",
        "is_weekend",
        "has_school_today",
        "has_school_next_day",
        "school_start",
        "school_end",
        "bedtime",
        "day_start",
        "daily_use_minutes",
        "daily_session_count",
    ]

    
    print("\nCONTEXTO DIARIO DEBUG\n")

    daily_behavior["daily_use_minutes"] = (
        daily_behavior["daily_use_minutes"].round(1)
    )

    print(
        daily_behavior[debug_columns]
        .to_string(index=False)
    )

    print("\nSESIONES DEBUG\n")

    debug_sessions = sessions.copy()

    debug_sessions["session_duration_minutes"] = (
        debug_sessions["session_duration_minutes"].round(2)
    )

    print(
        debug_sessions
        .head(30)
        .to_string(index=False)
    )

    # Inspecciona las ventanas de un día escolar y un sábado.
    for debug_day_index in (0, 5):

        day = daily_behavior.loc[
            daily_behavior["day_index"] == debug_day_index
        ].iloc[0]

        severity = float(
            population.loc[
                population["child_id"] == day["child_id"],
                "S",
            ].iloc[0]
        )

        windows = build_time_windows(
            day=day,
            severity=severity,
        )

        print(
            f"\n--- child_id={int(day['child_id'])}, "
            f"day_index={debug_day_index} ---"
        )

        validate_time_windows(windows)
        print_time_windows(windows)

    # ========================================================
    # VALIDACIÓN ESTADÍSTICA DE T
    # ========================================================

    # Crea una realización grande independiente de la muestra
    # de debug para validar las propiedades estadísticas de T.
    validation_seed_sequence = np.random.SeedSequence(
        config.CALIBRATION_SEED + 1
    )

    (
        validation_population_seed,
        validation_context_seed,
        validation_time_seed,
        validation_session_seed,
        validation_duration_seed,
        validation_scheduler_seed,
        validation_episode_seed,
        validation_category_seed,
        validation_target_seed,
    ) = validation_seed_sequence.spawn(9)

    validation_population = generate_population(
        n_children=config.N_CHILDREN_FINAL,
        seed=validation_population_seed,
    )

    validation_contexts = generate_daily_contexts(
        population=validation_population,
        seed=validation_context_seed,
        n_days=config.N_DAYS,
    )

    validation_time_rng = np.random.default_rng(
        validation_time_seed
    )

    validation_behavior = add_daily_use_time(
        contexts=validation_contexts,
        population=validation_population,
        rng=validation_time_rng,
    )

    validation_session_rng = np.random.default_rng(
        validation_session_seed
    )

    validation_behavior = add_daily_session_count(
        daily_behavior=validation_behavior,
        population=validation_population,
        rng=validation_session_rng,
    )

    validation_duration_rng = np.random.default_rng(
        validation_duration_seed
    )

    validation_sessions = build_session_table(
        daily_behavior=validation_behavior,
        rng=validation_duration_rng,
    )

    # Calendariza todas las sesiones de la muestra grande de validación.
    validation_scheduler_rng = np.random.default_rng(
        validation_scheduler_seed
    )

    validation_scheduled_sessions = schedule_all_sessions(
        sessions=validation_sessions,
        daily_behavior=validation_behavior,
        rng=validation_scheduler_rng,
        show_progress=False,
    )

    validate_scheduled_sessions(
        daily_behavior=validation_behavior,
        scheduled_sessions=validation_scheduled_sessions,
    )

    # Calcula los overlaps contextuales para la muestra grande.
    validation_scheduled_sessions = add_contextual_overlaps(
        scheduled_sessions=validation_scheduled_sessions,
        daily_behavior=validation_behavior,
    )

    validate_contextual_overlaps(
        daily_behavior=validation_behavior,
        scheduled_sessions=validation_scheduled_sessions,
    )

    diagnose_contextual_overlaps(
        daily_behavior=validation_behavior,
        scheduled_sessions=validation_scheduled_sessions,
    )

    # Genera episodios de foreground para la muestra grande.
    validation_episode_rng = np.random.default_rng(
        validation_episode_seed
    )

    validation_app_episodes = build_app_episode_table(
        scheduled_sessions=validation_scheduled_sessions,
        daily_behavior=validation_behavior,
        rng=validation_episode_rng,
    )

    validate_app_episodes(
        scheduled_sessions=validation_scheduled_sessions,
        app_episodes=validation_app_episodes,
    )

    diagnose_app_episodes(
        scheduled_sessions=validation_scheduled_sessions,
        app_episodes=validation_app_episodes,
    )

    # Genera preferencias y asigna categorías
    # para la muestra grande.
    validation_category_rng = np.random.default_rng(
        validation_category_seed
    )

    validation_category_preferences = (
        generate_child_category_preferences(
            daily_behavior=validation_behavior,
            rng=validation_category_rng,
        )
    )

    validation_app_episodes = assign_episode_categories(
        app_episodes=validation_app_episodes,
        category_preferences=validation_category_preferences,
        rng=validation_category_rng,
    )

    validate_app_categories(
        app_episodes=validation_app_episodes,
        category_preferences=validation_category_preferences,
    )

    diagnose_app_category_relationships(
        app_episodes=validation_app_episodes,
        daily_behavior=validation_behavior,
    )

    # Construye las features semanales observables
    # que posteriormente recibirá el modelo de ML.
    from build_features import (
        build_weekly_features,
        validate_weekly_features,
        diagnose_feature_relationships,
        diagnose_app_opening_redundancy,
    )

    validation_features = build_weekly_features(
        daily_behavior=validation_behavior,
        scheduled_sessions=validation_scheduled_sessions,
        app_episodes=validation_app_episodes,
    )

    validate_weekly_features(
        features=validation_features,
        expected_children=config.N_CHILDREN_FINAL,
    )

    diagnose_feature_relationships(
        validation_features
    )

    diagnose_app_opening_redundancy(
        features=validation_features,
        daily_behavior=validation_behavior,
    )

    # Genera el target sintético mediante un substream
    # independiente de los demás componentes del DGM.
    from generate_target import (
        generate_synthetic_target,
        validate_synthetic_target,
    )

    validation_target_rng = np.random.default_rng(
        validation_target_seed
    )

    validation_target = generate_synthetic_target(
        population=validation_population,
        rng=validation_target_rng,
    )

    validate_synthetic_target(
        target_data=validation_target,
        population=validation_population,
    )

    # Ensambla Dataset A y audita explícitamente
    # que ninguna variable interna genere leakage.
    from build_dataset import (
        build_dataset_a,
        validate_dataset_a,
        split_x_y,
        validate_x_y,
    )

    validation_dataset_a = build_dataset_a(
        features=validation_features,
        target_data=validation_target,
    )

    validate_dataset_a(
        dataset=validation_dataset_a,
        expected_children=config.N_CHILDREN_FINAL,
    )

    validation_X, validation_y = split_x_y(
        validation_dataset_a
    )

    validate_x_y(
        X=validation_X,
        y=validation_y,
        expected_children=config.N_CHILDREN_FINAL,
    )

    validate_scheduler_statistics(
        validation_scheduled_sessions
    )

    # Divide Dataset A en development y test
    # de forma reproducible y estratificada por edad.
    from split_dataset import (
        split_dataset_by_age,
        validate_dataset_split,
        build_model_matrices,
        validate_model_matrices,
    )

    development_dataset, test_dataset = split_dataset_by_age(
        dataset=validation_dataset_a,
        population=validation_population,
        seed=config.SPLIT_SEED,
    )

    validate_dataset_split(
        development=development_dataset,
        test=test_dataset,
        population=validation_population,
    )

    X_development, y_development = build_model_matrices(
        development_dataset
    )

    X_test, y_test = build_model_matrices(
        test_dataset
    )

    validate_model_matrices(
        X_development=X_development,
        y_development=y_development,
        X_test=X_test,
        y_test=y_test,
    )

    # Evalúa el baseline exclusivamente sobre development.
    # El conjunto test permanece completamente reservado.
    from evaluate_models import (
        evaluate_dummy_baseline,
        evaluate_linear_regression,
        evaluate_ridge_regression,
        evaluate_random_forest,
        evaluate_xgboost,
        evaluate_learning_curve,
        evaluate_feature_ablation,
        evaluate_oracle_models,
        audit_observable_signal_of_s,
        evaluate_final_test,
        save_final_model,
        validate_saved_model,
    )

    dummy_cv_results, dummy_cv_summary = (
        evaluate_dummy_baseline(
            X_development=X_development,
            y_development=y_development,
            development_dataset=development_dataset,
            population=validation_population,
        )
    )

    linear_cv_results, linear_cv_summary = (
        evaluate_linear_regression(
            X_development=X_development,
            y_development=y_development,
            development_dataset=development_dataset,
            population=validation_population,
        )
    )

    ridge_cv_results, ridge_cv_summary = (
        evaluate_ridge_regression(
            X_development=X_development,
            y_development=y_development,
            development_dataset=development_dataset,
            population=validation_population,
        )
    )

    random_forest_cv_results, random_forest_cv_summary = (
        evaluate_random_forest(
            X_development=X_development,
            y_development=y_development,
            development_dataset=development_dataset,
            population=validation_population,
        )
    )

    xgboost_cv_results, xgboost_cv_summary = (
        evaluate_xgboost(
            X_development=X_development,
            y_development=y_development,
            development_dataset=development_dataset,
            population=validation_population,
        )
    )

    learning_curve_summary = evaluate_learning_curve(
        X_development=X_development,
        y_development=y_development,
        development_dataset=development_dataset,
        population=validation_population,
    )

    ablation_summary = evaluate_feature_ablation(
        X_development=X_development,
        y_development=y_development,
        development_dataset=development_dataset,
        population=validation_population,
    )

    oracle_summary = evaluate_oracle_models(
        development_dataset=development_dataset,
        population=validation_population,
        y_development=y_development,
    )

    observable_s_signal = audit_observable_signal_of_s(
        development_dataset=development_dataset,
        population=validation_population,
    )

    final_model, final_test_results = evaluate_final_test(
        X_development=X_development,
        y_development=y_development,
        X_test=X_test,
        y_test=y_test,
    )

    save_final_model(
        final_model=final_model,
    )

    validate_saved_model(
        final_model=final_model,
        X_reference=X_development,
    )

    validate_daily_use_time(validation_behavior)
    
    validate_daily_session_count(validation_behavior)
    
    validate_session_durations(
        daily_behavior=validation_behavior,
        sessions=validation_sessions,
    )


if __name__ == "__main__":
    main()