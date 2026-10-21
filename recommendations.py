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
from typing import Iterable, Mapping
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


@dataclass(frozen=True)
class ActivityEligibility:
    """Restricciones operativas conocidas antes de ordenar actividades."""

    excluded_activity_ids: tuple[str, ...] = ()
    excluded_categories: tuple[str, ...] = ()
    allowed_activity_levels: tuple[str, ...] = (
        "calm",
        "moderate",
        "active",
    )
    allow_requires_other_person: bool = True
    allow_may_require_device_interaction: bool = True


# ============================================================
# CATÁLOGO PROVISIONAL REVISADO
# ============================================================

ACTIVITY_CATALOG: tuple[Activity, ...] = (

    # --------------------------------------------------------
    # MOVIMIENTO
    # --------------------------------------------------------

    Activity(
        activity_id="movement_dance_01",
        title="Bailá a tu manera",
        description=(
            "Necesitás: Una canción que conozcas. Si querés escucharla, un dispositivo para reproducirla.\n"
            "1. Elegí una canción que te guste. Podés ponerla o cantarla vos.\n"
            "2. Si usás el celular para escucharla, dejalo apoyado en un lugar seguro. No hace falta seguir mirando la pantalla.\n"
            "3. Mové las manos y los brazos al ritmo de la canción. Podés bailar sentado o de pie."
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
        title="Armá una cadena de movimientos",
        description=(
            "No necesitás materiales.\n"
            "1. Levantá las manos y después bajalas.\n"
            "2. Agregá otro movimiento que puedas hacer, como abrir y cerrar las manos.\n"
            "3. Repetí los movimientos en ese mismo orden. Podés hacerlos sentado o de pie."
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
            "Necesitás: Una pelota blanda o un par de medias enrolladas. Un lugar donde esté permitido jugar.\n"
            "1. Buscá un espacio libre de cosas que se puedan romper.\n"
            "2. Apoyá la pelota en el piso y hacela rodar suavemente hacia un lugar que elijas.\n"
            "3. Andá a buscarla y probá hacerla rodar otra vez."
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
    # CREATIVIDAD
    # --------------------------------------------------------

    Activity(
        activity_id="creative_character_01",
        title="Inventá un personaje",
        description=(
            "No necesitás materiales. Si querés dibujarlo, usá papel y lápiz.\n"
            "1. Imaginá un personaje. Puede ser una persona, un animal o un monstruo inventado.\n"
            "2. Elegí su nombre y algo que le guste hacer.\n"
            "3. Podés contar cómo es o dibujarlo."
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
        title="Combiná dos animales",
        description=(
            "No necesitás materiales. Si querés dibujar, usá papel y lápiz.\n"
            "1. Elegí dos animales que conozcas, por ejemplo, un gato y un pájaro.\n"
            "2. Imaginá un animal que tenga una parte de cada uno, como un gato con alas.\n"
            "3. Inventale un nombre. Podés contar cómo es o dibujarlo."
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
            "Necesitás: Papel y un lápiz o lápices de colores.\n"
            "1. Buscá el papel y los lápices.\n"
            "2. Elegí algo que te guste, como un animal, una persona o un lugar.\n"
            "3. Dibujalo como vos quieras. Si no sabés por dónde empezar, dibujá primero una parte."
        ),
        category="creative",
        interest_tags=(
            "drawing",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="calm",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id="creative_story_01",
        title="Inventá una historia",
        description=(
            "No necesitás materiales.\n"
            "1. Elegí quién aparece en tu historia: una persona, un animal o un personaje inventado.\n"
            "2. Pensá dónde está y qué le pasa. Por ejemplo: «Un gato encontró una puerta chiquita».\n"
            "3. Inventá qué sucede después. Podés contar la historia o imaginarla en silencio."
        ),
        category="creative",
        interest_tags=(
            "stories",
            "creative",
        ),
        allowed_contexts=(
            CONTEXT_VOLUNTARY,
            CONTEXT_GENERAL,
        ),
        activity_level="calm",
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    # --------------------------------------------------------
    # LECTURA
    # --------------------------------------------------------

    Activity(
        activity_id="reading_choose_01",
        title="Elegí algo para leer",
        description=(
            "Necesitás: Un libro o una historieta en papel.\n"
            "Si tenés un libro o historieta en papel, leé una parte a tu ritmo. También podés mirar sus ilustraciones."
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
            "Necesitás: Un libro o una historieta en papel, si lo tenés a mano.\n"
            "Buscá tu parte favorita de un libro o historieta en papel. Si no lo tenés a mano, recordá esa escena."
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
    # JUEGO LIBRE
    # --------------------------------------------------------

    Activity(
        activity_id="free_play_nearby_01",
        title="Jugá con algo que tengas cerca",
        description=(
            "Necesitás: Juguetes, cartas o bloques que puedas usar.\n"
            "1. Elegí un juguete, cartas o bloques que tengas a mano.\n"
            "2. Pensá qué podés hacer con lo que elegiste. Por ejemplo, si elegís un autito, armale un camino en el piso.\n"
            "3. Empezá a jugar. Si elegiste el autito, podés cambiar el camino o inventar qué pasa durante el viaje."
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
            "Necesitás: Bloques o cajas que tengas para jugar.\n"
            "Con bloques o cajas que tengas para jugar, armá una torre, un puente o lo que se te ocurra."
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
        title="Jugá a inventar con objetos",
        description=(
            "Necesitás: Uno o dos juguetes u objetos que puedas usar para jugar.\n"
            "Elegí uno o dos juguetes u objetos y jugá a que son personajes de una historia."
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
    # SOCIAL / FAMILIAR
    # --------------------------------------------------------

    Activity(
        activity_id="social_play_01",
        title="Jugá con alguien",
        description=(
            "Necesitás: Una persona de confianza que esté con vos y quiera jugar.\n"
            "1. Preguntale si tiene ganas de jugar con vos.\n"
            "2. Si quiere, elijan un juego que los dos conozcan.\n"
            "3. Por ejemplo, uno piensa en un animal y el otro hace preguntas para adivinarlo. Después cambien de turno. Si ahora no puede jugar, podés elegir otra actividad."
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
            "Necesitás: Una persona de confianza que esté con vos y quiera conversar.\n"
            "1. Preguntale si tiene un momento para escucharte.\n"
            "2. Si tenés ganas, contale algo de tu día. Puede ser algo que hiciste, que te gustó o que te sorprendió.\n"
            "3. Después podés preguntarle cómo estuvo su día y escucharla. Si no querés contar, elegí otra actividad."
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
        activity_id="social_create_together_01",
        title="Inventen algo entre dos",
        description=(
            "Necesitás: Una persona de confianza que esté con vos y quiera participar. Si eligen dibujar, papel y lápices.\n"
            "Con una persona de confianza que tenga ganas, inventen algo por turnos: una historia, un dibujo o un juego."
        ),
        category="social_family",
        interest_tags=(
            "social",
            "creative",
            "stories",
            "drawing",
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
            "Necesitás: Una persona de confianza que esté con vos y quiera contar una historia.\n"
            "Si una persona de confianza está con vos y quiere, pedile que te cuente una historia. Vos elegís el tema."
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
    # CALMA / DESCANSO
    # --------------------------------------------------------

    Activity(
        activity_id="quiet_story_ending_01",
        title="Inventá otro final",
        description=(
            "No necesitás materiales.\n"
            "Recordá una historia que te guste e imaginá otro final. Podés guardártelo para vos."
        ),
        category="quiet",
        interest_tags=(
            "stories",
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
        activity_id="quiet_draw_01",
        title="Hacé un dibujo tranquilo",
        description=(
            "Necesitás: Papel y un lápiz o lápices de colores.\n"
            "1. Buscá el papel y los lápices y elegí un lugar cómodo para dibujar.\n"
            "2. Dibujá algo que conozcas, como una flor, una casa o un animal. También podés dibujar otra cosa que te guste.\n"
            "3. Hacelo a tu ritmo. Cuando quieras parar, guardá el dibujo. No hace falta terminarlo hoy."
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


# Identificadores retirados de nuevas sugerencias, conservados para antecedentes.
RETIRED_ACTIVITY_IDS = frozenset({"social_help_01", "quiet_prepare_01"})
# Intereses históricos aceptados como entrada, sin transferirlos a otra actividad.
LEGACY_INTEREST_TAGS = frozenset({"helping", "organization", "writing"})


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
    eligibility: ActivityEligibility | None = None,
    n: int = 3,
    random_seed: int | None = None,
    selected_activity_counts: Mapping[str, int] | None = None,
) -> list[Activity]:
    """
    Selecciona actividades del catálogo.

    La versión v1 utiliza:
    - compatibilidad con contexto;
    - intereses opcionales;
    - penalización por repetición reciente;
    - variedad entre categorías.

    Las elecciones vinculadas pueden aportar un refuerzo leve y provisional.
    No representan realización ni eficacia de una actividad.
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

    eligibility_rules = (
        eligibility
        if eligibility is not None
        else ActivityEligibility()
    )

    valid_levels = {
        "calm",
        "moderate",
        "active",
    }

    if not set(eligibility_rules.allowed_activity_levels).issubset(valid_levels):
        raise ValueError(
            "allowed_activity_levels contiene niveles de actividad inválidos."
        )

    interests_set = {
        value.strip().lower()
        for value in (interests or [])
        if value.strip()
    }

    recently_shown_set = set(
        recently_shown_ids or []
    )

    choice_counts = selected_activity_counts or {}
    if any(
        not isinstance(activity_id, str)
        or not activity_id
        or type(count) is not int
        or count < 0
        for activity_id, count in choice_counts.items()
    ):
        raise ValueError("selected_activity_counts must contain nonnegative counts.")

    rng = random.Random(
        random_seed
    )

    candidates = [
        activity
        for activity in ACTIVITY_CATALOG
        if context in activity.allowed_contexts
    ]

    candidates = [
        activity
        for activity in candidates
        if activity.activity_id
        not in eligibility_rules.excluded_activity_ids
        and activity.category
        not in eligibility_rules.excluded_categories
        and activity.activity_level
        in eligibility_rules.allowed_activity_levels
        and (
            eligibility_rules.allow_requires_other_person
            or not activity.requires_other_person
        )
        and (
            eligibility_rules.allow_may_require_device_interaction
            or not activity.may_require_device_interaction
        )
    ]

    if context == CONTEXT_BEDTIME:
        candidates = [
            activity
            for activity in candidates
            if activity.bedtime_suitable
            and activity.activity_level == "calm"
        ]

    if len(candidates) == 0:
        return []

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

        # A single choice may be incidental; repeated choices get a small,
        # capped boost that cannot override the recent-offer penalty.
        choice_count = choice_counts.get(activity.activity_id, 0)
        if choice_count >= 2:
            score += min(0.20, 0.05 * (choice_count - 1))

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

        if len(selected) == min(n, len(candidates)):
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

            if len(selected) == min(n, len(candidates)):
                break

    return selected


# Validación inmediata al importar el módulo.
validate_catalog()
