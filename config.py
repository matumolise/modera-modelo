"""
Configuración central del DGM v1.0.

Este archivo contiene solamente parámetros y decisiones de configuración.
La lógica de generación se implementa en los demás módulos.

IMPORTANTE:
- Los parámetros numéricos del escenario Base son decisiones de ingeniería.
- No representan estimaciones clínicas ni poblacionales.
- Solo podrán recalibrarse durante la fase piloto por problemas de
  plausibilidad, degeneración o incoherencia matemática.
- Nunca se calibrarán utilizando el rendimiento posterior del modelo de ML.
"""

import math
from pathlib import Path


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
PILOT_DATA_DIR = DATA_DIR / "pilot"
FINAL_DATA_DIR = DATA_DIR / "final"

MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"


# ============================================================
# REPRODUCIBILIDAD
# ============================================================

# Seed utilizado durante la calibración del DGM con datasets piloto.
CALIBRATION_SEED = 123

# Seed utilizado para generar el dataset final una vez congelado el DGM.
GENERATION_SEED = 42

# Seed utilizado para separar development y test.
SPLIT_SEED = 42

# Seed reservado para validación cruzada cuando el método lo requiera.
CV_SEED = 42


# ============================================================
# POBLACIÓN
# ============================================================

MIN_AGE = 6
MAX_AGE = 12

AGES = list(range(MIN_AGE, MAX_AGE + 1))

# Dataset final: 200 niños por cada una de las 7 edades.
N_CHILDREN_FINAL = 1400
N_CHILDREN_PER_AGE = 200

# Ventana inicial de observación.
N_DAYS = 7

# El dispositivo monitorizado se asume de uso individual del niño.
ASSUME_PERSONAL_DEVICE = True


# ============================================================
# VARIABLES LATENTES
# ============================================================

# S, B, F y U se generan como N(0, 1), de forma independiente
# en el escenario Base.
LATENT_MEAN = 0.0
LATENT_STD = 1.0

# No se definen correlaciones entre S, B, F y U en Base v1.
LATENTS_INDEPENDENT = True


# ============================================================
# CONTEXTO ESCOLAR
# ============================================================

SCHOOL_MODES = (
    "morning",
    "afternoon",
    "full_day",
)

# Proporciones del escenario sintético Base.
# Son diseño experimental y NO representan la demografía argentina.
SCHOOL_MODE_PROBABILITIES = {
    "morning": 0.40,
    "afternoon": 0.40,
    "full_day": 0.20,
}

# Horarios escolares de referencia.
# Se almacenan como texto y se convertirán a datetime/minutos
# dentro del módulo correspondiente.
SCHOOL_BASE_SCHEDULES = {
    "morning": {
        "start": "08:00",
        "end": "12:15",
    },
    "afternoon": {
        "start": "13:00",
        "end": "17:15",
    },
    "full_day": {
        "start": "08:15",
        "end": "16:20",
    },
}

# Se aplica el mismo desplazamiento a inicio y fin,
# preservando la duración original de la jornada.
SCHOOL_TIME_SHIFT_MIN_MINUTES = -15
SCHOOL_TIME_SHIFT_MAX_MINUTES = 15

# Calendario simplificado del DGM Base:
# 0=lunes ... 6=domingo.
SCHOOL_WEEKDAYS = (0, 1, 2, 3, 4)


# ============================================================
# BEDTIME
# ============================================================

# Bedtime significa horario habitual de ACOSTARSE.
# No representa el momento real de inicio del sueño.
BEDTIME_SCHOOL_MIN = "21:30"
BEDTIME_SCHOOL_MAX = "23:15"

# En una noche previa a un día sin colegio,
# el bedtime puede desplazarse entre 0 y 75 minutos.
NON_SCHOOL_BEDTIME_DELAY_MIN_MINUTES = 0
NON_SCHOOL_BEDTIME_DELAY_MAX_MINUTES = 75

# No existe efecto directo de edad o school_mode sobre bedtime
# en el escenario Base v1.
AGE_AFFECTS_BEDTIME = False
SCHOOL_MODE_AFFECTS_BEDTIME = False


# ============================================================
# INICIO OPERATIVO DEL DÍA
# ============================================================

# day_start NO representa la hora real de despertar.
# Es la frontera operativa entre el período overnight
# y el comienzo del período diurno del scheduler.

# Para turno mañana y jornada completa:
# day_start = school_start - U(60, 90 minutos).
DAY_START_BEFORE_SCHOOL_MIN_MINUTES = 60
DAY_START_BEFORE_SCHOOL_MAX_MINUTES = 90

# Para turno tarde.
DAY_START_AFTERNOON_MIN = "07:30"
DAY_START_AFTERNOON_MAX = "09:00"

# Para días sin colegio / fin de semana.
DAY_START_NO_SCHOOL_MIN = "08:30"
DAY_START_NO_SCHOOL_MAX = "10:00"


# ============================================================
# PRE-BEDTIME
# ============================================================

# Ventana temporal previa al bedtime.
# No implica que el niño se esté preparando para dormir.
PRE_BEDTIME_WINDOW_MINUTES = 120

# En días sin colegio, separa operativamente la mañana
# del resto del tiempo libre diurno.
# No representa una regla clínica ni un horario de actividad obligatorio.
NO_SCHOOL_MORNING_END = "12:00"


# ============================================================
# TIEMPO TOTAL DE USO DIARIO T
# ============================================================

# Pesos relativos del predictor de tiempo.
# Mantienen la jerarquía B > S > edad.
TIME_WEIGHT_B = 0.529
TIME_WEIGHT_S = 0.353
TIME_WEIGHT_AGE = 0.118

# Mediana basal sintética aproximada de 155 minutos.
TIME_BASE_MEDIAN_MINUTES = 155.0

# alpha_T se deriva automáticamente de la mediana basal.
TIME_ALPHA = math.log(TIME_BASE_MEDIAN_MINUTES)

# Intensidad total de los efectos B/S/edad.
TIME_KAPPA = 0.35

# Efecto multiplicativo de fin de semana en escala log.
TIME_WEEKEND_EFFECT = 0.15

# Variabilidad diaria intrapersonal en escala log.
TIME_DAILY_SIGMA = 0.35

# Límite físico absoluto: un día no puede superar 24 horas.
MAX_DAILY_MINUTES = 24 * 60


# ============================================================
# CANTIDAD DE SESIONES N
# ============================================================

# Pesos relativos del predictor de sesiones.
# Mantienen la jerarquía F > B > S.
SESSION_WEIGHT_F = 0.5625
SESSION_WEIGHT_B = 0.25
SESSION_WEIGHT_S = 0.1875

# Media basal de la Negative Binomial ANTES del zero-truncation.
SESSION_BASE_MEAN = 24.0

# alpha_N se deriva automáticamente de la media basal pre-truncamiento.
SESSION_ALPHA = math.log(SESSION_BASE_MEAN)

# Intensidad total del predictor de sesiones.
SESSION_KAPPA = 0.40

# Parámetro de dispersión NB2:
# Var(N) = mu + mu^2 / r
SESSION_NB_DISPERSION_R = 8.0

# El escenario Base supone al menos una sesión por día.
SESSION_ZERO_TRUNCATED = True

# No hay efecto weekend directo adicional en N.
SESSION_WEEKEND_EFFECT = 0.0


# ============================================================
# DURACIONES DE SESIONES
# ============================================================

# Las duraciones se obtendrán mediante pesos Gamma normalizados.
SESSION_DURATION_GAMMA_SHAPE = 1.0
SESSION_DURATION_GAMMA_SCALE = 1.0

# d_min fue eliminado del diseño y NO debe reintroducirse.


# ============================================================
# SCHEDULER TEMPORAL
# ============================================================

# Intensidades relativas por unidad de tiempo.
# NO son probabilidades directas de cada ventana.
SCHEDULER_WEIGHTS = {
    "morning_free": 1.00,
    "school": 0.20,
    "daytime_free": 1.40,
    "pre_bedtime": 1.20,
    "post_bedtime_overnight": 0.15,
}

# Efecto débil de S sobre la intensidad posterior al bedtime:
# w_post = w0 * exp(beta_S_night * S)
BETA_S_NIGHT = 0.10

# Cada instante deberá pertenecer a una sola ventana temporal.
SCHEDULER_WINDOWS_MUTUALLY_EXCLUSIVE = True

# Las sesiones nunca pueden solaparse.
ALLOW_SESSION_OVERLAP = False

# Una sesión puede atravesar bedtime o medianoche sin dividirse.
ALLOW_SESSION_ACROSS_BEDTIME = True
# En Base v1 las sesiones sintéticas no atraviesan medianoche.
# Esto preserva la conservación exacta de T y N por día calendario.
# El uso de madrugada sigue representándose mediante sesiones
# pertenecientes al día calendario siguiente.
ALLOW_SESSION_ACROSS_MIDNIGHT = False

# Cantidad máxima de intentos para reconstruir el scheduling completo
# de un niño-día si alguna sesión no puede colocarse.
SCHEDULER_MAX_DAY_RETRIES = 100


# ============================================================
# EPISODIOS DE APLICACIONES
# ============================================================

# rho_i = exp(alpha_M + kappa_F * F_i)
#
# alpha_M = -ln(6), calculado programáticamente.
APP_EPISODE_ALPHA = -math.log(6.0)

# Influencia de F sobre fragmentación intra-sesión.
APP_EPISODE_KAPPA_F = 0.30

# La duración D_s utilizada en la ecuación se expresa en minutos.
APP_EPISODE_DURATION_UNIT = "minutes"

# M_s = 1 + Poisson(D_s * rho_i)
APP_EPISODE_MIN_COUNT = 1

# S no influye directamente sobre la cantidad de episodios.
S_DIRECT_EFFECT_ON_APP_EPISODES = 0.0

# Las duraciones de episodios se repartirán mediante Gamma(1)
# normalizada dentro de cada sesión.
APP_EPISODE_GAMMA_SHAPE = 1.0
APP_EPISODE_GAMMA_SCALE = 1.0


# ============================================================
# CATEGORÍAS DE APLICACIONES
# ============================================================

APP_CATEGORIES = (
    "games",
    "social",
    "entertainment",
    "education",
    "other",
)

# Dirichlet simétrica para generar preferencias individuales.
CATEGORY_DIRICHLET_ALPHA = (
    1.5,
    1.5,
    1.5,
    1.5,
    1.5,
)

# No existe efecto directo de S ni edad sobre las categorías
# en el escenario Base v1.
S_AFFECTS_CATEGORIES = False
AGE_AFFECTS_CATEGORIES = False

# Los shares se calcularán sobre minutos efectivamente
# atribuidos a aplicaciones.
CATEGORY_SHARE_DENOMINATOR = "total_attributed_app_minutes"


# ============================================================
# TARGET SINTÉTICO
# ============================================================

# Y* = S + beta_U * U + epsilon
TARGET_BETA_S = 1.0
TARGET_BETA_U = 0.45

# epsilon ~ N(0, sigma_target^2)
TARGET_NOISE_SIGMA = 0.25

# El target final se obtiene mediante:
# Y = 1 + 4 * sigmoid(Y*)
TARGET_MIN = 1.0
TARGET_MAX = 5.0


# ============================================================
# FEATURES DEL DATASET A
# ============================================================

# Whitelist explícita.
# Ninguna columna que no aparezca aquí podrá entrar
# accidentalmente en X.
DATASET_A_FEATURES = [
    "age_scaled",
    "mean_daily_use_minutes",
    "mean_daily_session_count",
    "median_session_duration",
    "mean_daily_app_openings",
    "post_bedtime_use_ratio",
    "school_use_ratio",
    "games_share",
    "social_share",
    "entertainment_share",
    "education_share",
]

# mean_daily_app_openings es candidata preespecificada,
# pero su permanencia definitiva dependerá exclusivamente del
# sanity check de redundancia estructural T-N-openings.
PROVISIONAL_FEATURES = [
    "mean_daily_app_openings",
]

# Variables explícitamente prohibidas como predictores.
FORBIDDEN_MODEL_FEATURES = [
    "child_id",
    "age",
    "S",
    "B",
    "F",
    "U",
    "y_star",
    "target_noise",
    "scenario",
    "seed",
]


# ============================================================
# SPLIT DEL DATASET FINAL
# ============================================================

TEST_CHILDREN_PER_AGE = 40
DEVELOPMENT_CHILDREN_PER_AGE = 160

N_TEST_CHILDREN = 280
N_DEVELOPMENT_CHILDREN = 1120

TEST_FRACTION = 0.20

CV_FOLDS = 5


# ============================================================
# ESCENARIOS DE SENSIBILIDAD
# ============================================================

SENSITIVITY_SCENARIOS = (
    "weak",
    "base",
    "strong",
    "null",
)

BASE_SCENARIO = "base"


# ============================================================
# CONFIGURACIÓN DE DEBUG
# ============================================================

# Estos tamaños se usan únicamente para pruebas manuales
# antes de generar datasets grandes.
DEBUG_N_CHILDREN = 10
DEBUG_N_DAYS = 1