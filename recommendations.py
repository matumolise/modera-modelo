"""
Motor de recomendaciones del MVP.

Responsabilidades:
- mantener un catálogo curado de actividades;
- filtrar actividades según contexto;
- considerar intereses opcionales;
- evitar repetición excesiva;
- mantener variedad entre categorías;
- devolver un conjunto reducido de alternativas.

IMPORTANTE:
Este módulo NO diagnostica PMU.
NO utiliza umbrales clínicos.
NO asume que una actividad seleccionada fue realizada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import random


# ============================================================
# CONTEXTOS
# ============================================================

CONTEXT_VOLUNTARY = "voluntary"
CONTEXT_BEDTIME = "bedtime"
CONTEXT_GENERAL = "general"


# ============================================================
# ACTIVIDAD
# ============================================================

@dataclass(frozen=True)
class Activity:
    activity_id: str
    title: str
    description: str
    category: str
    interest_tags: tuple[str, ...]
    allowed_contexts: tuple[str, ...]
    activity_level: str
    bedtime_suitable: bool
    requires_other_person: bool
    may_require_device_interaction: bool


# ============================================================
# CATÁLOGO V1
# ============================================================

ACTIVITY_CATALOG: tuple[Activity, ...] = (

    # --------------------------------------------------------
    # MOVEMENT
    # --------------------------------------------------------

    Activity(
        activity_id="movement_dance_01",
        title="Bailá una canción",
        description=(
            "Elegí una canción que te guste, "
            "dejá el celular y bailá mientras suena."
        ),
        category="movement",
        interest_tags=(
            "music",
            "dance",
            "movement",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="active",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=True,
    ),

    Activity(
        activity_id="movement_sequence_01",
        title="Armá una secuencia de movimientos",
        description=(
            "Elegí tres movimientos que puedas hacer, "
            "como saltar, girar o agacharte, "
            "y tratá de repetir la secuencia."
        ),
        category="movement",
        interest_tags=(
            "movement",
            "sports",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="active",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="movement_ball_01",
        title="Jugá con una pelota",
        description=(
            "Si tenés una pelota cerca y un lugar seguro, "
            "elegí una forma de jugar con ella."
        ),
        category="movement",
        interest_tags=(
            "sports",
            "movement",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="active",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # CREATIVE
    # --------------------------------------------------------

    Activity(
        activity_id="creative_character_01",
        title="Inventá un personaje",
        description=(
            "Inventá un personaje nuevo y dibujá cómo sería."
        ),
        category="creative",
        interest_tags=(
            "drawing",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="creative_animal_01",
        title="Creá un animal imaginario",
        description=(
            "Mezclá características de animales que conozcas "
            "e inventá uno nuevo para dibujar."
        ),
        category="creative",
        interest_tags=(
            "drawing",
            "animals",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="creative_favorite_01",
        title="Dibujá algo que te guste",
        description=(
            "Elegí un personaje, lugar, objeto o cualquier "
            "cosa que tengas ganas de dibujar."
        ),
        category="creative",
        interest_tags=(
            "drawing",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="creative_story_01",
        title="Inventá una historia",
        description=(
            "Inventá una historia corta. "
            "Podés escribirla, dibujarla o hacer las dos cosas."
        ),
        category="creative",
        interest_tags=(
            "writing",
            "drawing",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # READING
    # --------------------------------------------------------

    Activity(
        activity_id="reading_choose_01",
        title="Elegí algo para leer",
        description=(
            "Buscá un libro, cuento o cómic "
            "que tengas ganas de leer."
        ),
        category="reading",
        interest_tags=(
            "reading",
            "books",
            "comics",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="reading_favorite_01",
        title="Volvé a una historia que te guste",
        description=(
            "Elegí un libro, cuento o cómic que ya conozcas "
            "y buscá una parte que quieras volver a leer."
        ),
        category="reading",
        interest_tags=(
            "reading",
            "books",
            "comics",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # FREE PLAY
    # --------------------------------------------------------

    Activity(
        activity_id="free_play_nearby_01",
        title="Jugá con algo que tengas cerca",
        description=(
            "Elegí un juguete, cartas, bloques u otra cosa "
            "que tengas ganas de usar y empezá a jugar."
        ),
        category="free_play",
        interest_tags=(
            "toys",
            "games",
            "free_play",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="moderate",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="free_play_build_01",
        title="Construí algo",
        description=(
            "Si tenés bloques, piezas u objetos para construir, "
            "elegí qué querés crear y empezá."
        ),
        category="free_play",
        interest_tags=(
            "building",
            "creative",
            "toys",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="moderate",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="free_play_story_01",
        title="Creá una historia con tus juguetes",
        description=(
            "Elegí algunos juguetes y pensá qué historia "
            "podría pasarles."
        ),
        category="free_play",
        interest_tags=(
            "toys",
            "creative",
            "stories",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="moderate",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # SOCIAL / FAMILY
    # --------------------------------------------------------

    Activity(
        activity_id="social_play_01",
        title="Jugá con alguien",
        description=(
            "Si hay alguien de confianza cerca, "
            "preguntale si quiere jugar a algo con vos."
        ),
        category="social_family",
        interest_tags=(
            "social",
            "games",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="moderate",
        bedtime_suitable=False,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="social_talk_01",
        title="Contá algo de tu día",
        description=(
            "Si tenés ganas, contale a alguien de confianza "
            "algo divertido o interesante que te haya pasado."
        ),
        category="social_family",
        interest_tags=(
            "social",
            "conversation",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="social_help_01",
        title="Ayudá con algo",
        description=(
            "Si hay alguien cerca, preguntale si necesita "
            "ayuda con alguna tarea sencilla."
        ),
        category="social_family",
        interest_tags=(
            "social",
            "helping",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="moderate",
        bedtime_suitable=False,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="social_story_01",
        title="Escuchá una historia",
        description=(
            "Si hay alguien de confianza con quien tengas ganas "
            "de hablar, preguntale si quiere contarte una historia "
            "o una anécdota."
        ),
        category="social_family",
        interest_tags=(
            "social",
            "conversation",
            "stories",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # QUIET / BEDTIME
    # --------------------------------------------------------

    Activity(
        activity_id="quiet_prepare_01",
        title="Prepará algo para mañana",
        description=(
            "Elegí alguna cosa sencilla que puedas dejar lista "
            "para mañana, como tu mochila, ropa o materiales."
        ),
        category="quiet",
        interest_tags=(
            "organization",
        ),
        allowed_contexts=(
            CONTEXT_BEDTIME,
            CONTEXT_GENERAL,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="quiet_draw_01",
        title="Hacé un dibujo tranquilo",
        description=(
            "Elegí libremente algo que tengas ganas de dibujar "
            "mientras te preparás para terminar el día."
        ),
        category="quiet",
        interest_tags=(
            "drawing",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_BEDTIME,
        ),
        activity_level="calm",
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),
)


# ============================================================
# VALIDACIÓN DEL CATÁLOGO
# ============================================================

def validate_catalog() -> None:
    """Comprueba invariantes básicas del catálogo."""

    activity_ids = [
        activity.activity_id
        for activity in ACTIVITY_CATALOG
    ]

    if len(activity_ids) != len(set(activity_ids)):
        raise ValueError(
            "Hay activity_id duplicados en el catálogo."
        )

    valid_levels = {
        "calm",
        "moderate",
        "active",
    }

    valid_contexts = {
        CONTEXT_VOLUNTARY,
        CONTEXT_BEDTIME,
        CONTEXT_GENERAL,
    }

    for activity in ACTIVITY_CATALOG:

        if not activity.title.strip():
            raise ValueError(
                f"{activity.activity_id}: title vacío."
            )

        if not activity.description.strip():
            raise ValueError(
                f"{activity.activity_id}: description vacío."
            )

        if activity.activity_level not in valid_levels:
            raise ValueError(
                f"{activity.activity_id}: "
                "activity_level inválido."
            )

        if not set(
            activity.allowed_contexts
        ).issubset(valid_contexts):
            raise ValueError(
                f"{activity.activity_id}: "
                "contexto inválido."
            )

        if (
            CONTEXT_BEDTIME
            in activity.allowed_contexts
            and not activity.bedtime_suitable
        ):
            raise ValueError(
                f"{activity.activity_id}: "
                "permitida en bedtime pero "
                "bedtime_suitable=False."
            )


# ============================================================
# SELECTOR V1
# ============================================================

def recommend_activities(
    context: str,
    interests: Iterable[str] | None = None,
    recently_shown_ids: Iterable[str] | None = None,
    n: int = 3,
    random_seed: int | None = None,
) -> list[Activity]:
    """
    Selecciona actividades del catálogo.

    La versión v1 utiliza:
    - compatibilidad con contexto;
    - intereses opcionales;
    - penalización por repetición reciente;
    - variedad entre categorías.

    NO aprende todavía de la respuesta histórica del niño.
    La interfaz queda preparada para evolucionar posteriormente.
    """

    if n <= 0:
        raise ValueError(
            "n debe ser mayor que 0."
        )

    valid_contexts = {
        CONTEXT_VOLUNTARY,
        CONTEXT_BEDTIME,
        CONTEXT_GENERAL,
    }

    if context not in valid_contexts:
        raise ValueError(
            f"Contexto inválido: {context}"
        )

    interests_set = {
        value.strip().lower()
        for value in (interests or [])
        if value.strip()
    }

    recently_shown_set = set(
        recently_shown_ids or []
    )

    rng = random.Random(
        random_seed
    )

    candidates = [
        activity
        for activity in ACTIVITY_CATALOG
        if context in activity.allowed_contexts
    ]

    if context == CONTEXT_BEDTIME:
        candidates = [
            activity
            for activity in candidates
            if activity.bedtime_suitable
            and activity.activity_level == "calm"
        ]

    if len(candidates) < n:
        raise ValueError(
            "No hay suficientes actividades compatibles "
            "con el contexto solicitado."
        )

    # --------------------------------------------------------
    # PUNTAJE BASE
    # --------------------------------------------------------

    scored_candidates = []

    for activity in candidates:

        score = 0.0

        # Preferencia inicial opcional.
        matching_interests = (
            interests_set
            & {
                tag.lower()
                for tag in activity.interest_tags
            }
        )

        if matching_interests:
            score += 1.0

        # Evita mostrar excesivamente lo mismo.
        if activity.activity_id in recently_shown_set:
            score -= 2.0

        # Pequeño componente aleatorio para mantener variedad.
        score += rng.uniform(
            0.0,
            0.25,
        )

        scored_candidates.append(
            (
                score,
                activity,
            )
        )

    scored_candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # --------------------------------------------------------
    # VARIEDAD ENTRE CATEGORÍAS
    # --------------------------------------------------------

    selected = []
    selected_categories = set()

    # Primera pasada:
    # intentar categorías diferentes.
    for _, activity in scored_candidates:

        if activity.category in selected_categories:
            continue

        selected.append(
            activity
        )

        selected_categories.add(
            activity.category
        )

        if len(selected) == n:
            break

    # Segunda pasada:
    # si faltan actividades, completar aunque repita categoría.
    if len(selected) < n:

        selected_ids = {
            activity.activity_id
            for activity in selected
        }

        for _, activity in scored_candidates:

            if activity.activity_id in selected_ids:
                continue

            selected.append(
                activity
            )

            if len(selected) == n:
                break

    if len(selected) != n:
        raise RuntimeError(
            "No fue posible seleccionar la cantidad "
            "solicitada de actividades."
        )

    return selected


# Validación inmediata al importar el módulo.
validate_catalog()