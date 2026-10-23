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

    def __post_init__(self):
        # Aplicar la misma compatibilidad en selección directa, HTTP y coordinador.
        object.__setattr__(self, "excluded_activity_ids",
                           _expand_merged_activity_exclusions(self.excluded_activity_ids))


# ============================================================
# CATÁLOGO PROVISIONAL REVISADO
# ============================================================

ACTIVITY_CATALOG: tuple[Activity, ...] = (
    Activity(
        activity_id='movement_dance_01',
        title='Bailá al ritmo de tu canción',
        description=(
            'Necesitás: Un dispositivo para escuchar música, si querés poner una canción. Si preferís cantarla, no hace falta.\n'
            '1. Elegí una canción que te guste. Podés ponerla o cantarla vos.\n'
            '2. Si usás el celular, dejalo apoyado en un lugar seguro para tener las manos libres.\n'
            '3. Mové las manos, la cabeza o todo el cuerpo al ritmo de la canción. Podés bailar sentado o de pie.\n'
            '4. ¿Te animás a cantar o a dar palmas siguiendo el ritmo? Probá como te salga.'
        ),
        category='movement',
        interest_tags=('music', 'dance', 'movement'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='active',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=True,
    ),

    Activity(
        activity_id='movement_sequence_01',
        title='Sumá movimientos a tu secuencia',
        description=(
            'No necesitás materiales. La música es opcional. Si la ponés desde el celular, dejalo apoyado en un lugar seguro.\n'
            '1. Levantá las manos y después bajalas.\n'
            '2. Sumá otro movimiento que puedas hacer, como abrir y cerrar las manos.\n'
            '3. Agregá un movimiento con otra parte del cuerpo, por ejemplo, mover la cabeza hacia los lados.\n'
            '4. Repetí la secuencia en ese orden, a tu ritmo. Podés hacerlo sentado o de pie.'
        ),
        category='movement',
        interest_tags=('movement', 'sports'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='active',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=True,
    ),

    Activity(
        activity_id='movement_ball_01',
        title='Jugá con una pelota',
        description=(
            'Necesitás: Una pelota blanda o un par de medias enrolladas y un espacio donde esté permitido jugar.\n'
            '1. Buscá un lugar libre de objetos que se puedan romper.\n'
            '2. Elegí cómo jugar: hacé rodar la pelota por el piso, pasala de una mano a otra o apretala varias veces.\n'
            '3. Si tenés espacio y está permitido, también podés patearla suave o lanzarla suavemente con la mano. Elegí un movimiento que puedas hacer.'
        ),
        category='movement',
        interest_tags=('sports', 'movement'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='active',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='creative_character_story_01',
        title='Inventá un personaje y su historia',
        description=(
            'Necesitás: Papel y lápices solo si querés dibujar o escribir. Para imaginar no necesitás materiales.\n'
            '1. Imaginá un personaje: una persona, un animal o un monstruo, real o inventado.\n'
            '2. Elegí su nombre y algo que le guste hacer.\n'
            '3. Pensá qué le pasa y cómo se siente. Por ejemplo, encontró una puerta chiquita. ¿Qué hay del otro lado?\n'
            '4. Podés imaginar su historia en silencio, contarla, escribirla o dibujarla.'
        ),
        category='creative',
        interest_tags=('creative', 'stories', 'drawing', 'writing'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='creative_animal_01',
        title='Inventá un animal',
        description=(
            'Necesitás: Papel y lápices solo si querés dibujar. Para imaginar no necesitás materiales.\n'
            '1. Inventá un animal. Podés combinar dos que conozcas, como un gato con alas.\n'
            '2. Ponele un nombre y elegí de qué color es.\n'
            '3. Imaginá dónde vive, qué hace o quiénes son sus amigos. Podés contarlo, imaginarlo en silencio o dibujarlo.'
        ),
        category='creative',
        interest_tags=('drawing', 'animals', 'creative'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='creative_favorite_01',
        title='Dibujá algo que te guste',
        description=(
            'Necesitás: Papel y un lápiz o lápices de colores.\n'
            '1. Buscá el papel y los lápices.\n'
            '2. Elegí algo para dibujar, como un animal, una persona o algo que veas por la ventana o dentro de tu casa.\n'
            '3. Empezá por una parte y seguí de a poco. Hacelo como te salga.'
        ),
        category='creative',
        interest_tags=('drawing', 'creative'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='calm',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='reading_choose_01',
        title='Elegí algo para leer o mirar',
        description=(
            'Necesitás: Un libro o una historieta en papel. También puede ser un libro con ilustraciones.\n'
            '1. Buscá algo para leer o mirar y elegí un lugar cómodo.\n'
            '2. Mirá las ilustraciones o leé una parte, en voz alta o en silencio.\n'
            '3. Seguí a tu ritmo. No hace falta terminarlo ahora.'
        ),
        category='reading',
        interest_tags=('reading', 'books', 'comics'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='reading_favorite_01',
        title='Volvé a tu historia favorita',
        description=(
            'Necesitás: Un libro o una historieta en papel solo si querés releer. Para recordar la historia no necesitás materiales.\n'
            '1. Elegí una historia o un cuento que te guste mucho.\n'
            '2. Si lo tenés a mano, volvé a tu parte favorita. Si no, recordá qué pasaba y quiénes aparecían.\n'
            '3. Releé o imaginá esa escena a tu ritmo.'
        ),
        category='reading',
        interest_tags=('reading', 'books', 'comics'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='free_play_nearby_01',
        title='Jugá con tu juguete favorito',
        description=(
            'Necesitás: Un juguete que puedas usar. Si elegís cartas, un juego que ya conozcas.\n'
            '1. Buscá tu juguete favorito y un lugar cómodo para jugar.\n'
            '2. Si es un autito, armale un camino. Si es un muñeco, invitá a tu personaje a tomar el té o a dar un paseo imaginario.\n'
            '3. Elegí una de esas ideas y empezá a jugar. Si elegiste cartas, jugá a un juego que conozcas.'
        ),
        category='free_play',
        interest_tags=('toys', 'games', 'free_play'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='moderate',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='free_play_build_01',
        title='Construí un puente o una torre',
        description=(
            'Necesitás: Bloques o cajas que tengas para jugar.\n'
            '1. Juntá los bloques o las cajas y elegí un lugar para construir.\n'
            '2. ¿Querés hacer una torre? Apilá las piezas. ¿Un puente? Probá poner una pieza sobre dos apoyos.\n'
            '3. Agregá otras piezas para seguir tu construcción.'
        ),
        category='free_play',
        interest_tags=('building', 'creative', 'toys'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='moderate',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='free_play_story_01',
        title='Inventá una historia con tus juguetes',
        description=(
            'Necesitás: Dos juguetes u objetos que puedas usar para jugar.\n'
            '1. Elegí dos juguetes y decidí quién es cada personaje.\n'
            '2. Imaginá que se encuentran. ¿Dónde están y qué se dicen?\n'
            '3. Contá o representá qué les pasa después.'
        ),
        category='free_play',
        interest_tags=('toys', 'creative', 'stories'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='moderate',
        bedtime_suitable=False,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='social_play_01',
        title='Invitá a alguien a jugar',
        description=(
            'Necesitás: Una persona de confianza que esté con vos y quiera jugar.\n'
            '1. Invitá a jugar a alguien que te acompañe. Si ahora no puede, podés elegir otra actividad.\n'
            '2. Elijan un juego. Por ejemplo, uno representa un animal sin hablar y el otro intenta adivinarlo. Después cambian de turno.\n'
            '3. También pueden jugar a adivinar con preguntas: uno piensa un animal y el otro pregunta si vuela, nada o vive en la tierra.'
        ),
        category='social_family',
        interest_tags=('social', 'games'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='moderate',
        bedtime_suitable=False,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='social_conversation_story_01',
        title='Compartí una charla o una historia',
        description=(
            'Necesitás: Una persona de confianza que esté con vos y quiera conversar o contar una historia.\n'
            '1. Preguntale si tiene un momento para compartir con vos. Si ahora no puede, elegí otra actividad.\n'
            '2. Podés contarle algo de tu día, como algo que te gustó o te sorprendió, y preguntarle cómo estuvo el suyo.\n'
            '3. Si preferís escuchar, pedile que te cuente una historia y elegí el tema. No hace falta contar algo personal.'
        ),
        category='social_family',
        interest_tags=('social', 'conversation', 'stories'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='social_create_together_01',
        title='Creá algo con alguien',
        description=(
            'Necesitás: Una persona de confianza que esté con vos y quiera participar. Si eligen dibujar, papel y lápices.\n'
            '1. Invitá a alguien a crear una historia, un dibujo o un juego juntos. Si ahora no puede, elegí otra actividad.\n'
            '2. Si eligen una historia, uno dice cómo empieza y el otro agrega qué pasa después. Si eligen dibujar, agreguen una parte cada uno.\n'
            '3. Sigan por turnos para completar su creación.'
        ),
        category='social_family',
        interest_tags=('social', 'creative', 'stories', 'drawing'),
        allowed_contexts=('voluntary', 'general'),
        activity_level='moderate',
        bedtime_suitable=False,
        requires_other_person=True,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='quiet_story_ending_01',
        title='Inventá otro final',
        description=(
            'No necesitás materiales. Podés hacerlo solo o compartirlo con alguien de confianza que esté con vos.\n'
            '1. Recordá una historia que te guste y cómo termina.\n'
            '2. Imaginá qué pasaría si terminara de otra manera.\n'
            '3. Podés guardarte ese final para vos o contárselo a quien te acompañe, si tiene ganas de escucharlo.'
        ),
        category='quiet',
        interest_tags=('stories', 'creative'),
        allowed_contexts=('voluntary', 'general', 'bedtime'),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

    Activity(
        activity_id='quiet_draw_01',
        title='Dibujá a tu ritmo',
        description=(
            'Necesitás: Papel y un lápiz o lápices de colores.\n'
            '1. Buscá el papel y los lápices y elegí un lugar cómodo.\n'
            '2. Dibujá algo que te guste, como una flor, una casa o un animal. Hacelo a tu ritmo.\n'
            '3. Cuando quieras parar, guardá el dibujo y preparate para descansar. No hace falta terminarlo hoy.'
        ),
        category='quiet',
        interest_tags=('drawing', 'creative'),
        allowed_contexts=('bedtime',),
        activity_level='calm',
        bedtime_suitable=True,
        requires_other_person=False,
        may_require_device_interaction=False,
    ),

)


# Identificadores retirados de nuevas sugerencias, conservados para antecedentes.
RETIRED_ACTIVITY_IDS = frozenset({
    "social_help_01", "quiet_prepare_01", "creative_character_01",
    "creative_story_01", "social_talk_01", "social_story_01",
})

# La fusión no es un alias histórico. Una exclusión previa bloquea la nueva propuesta.
ACTIVITY_MERGE_PREDECESSORS = {
    "creative_character_story_01": frozenset({"creative_character_01", "creative_story_01"}),
    "social_conversation_story_01": frozenset({"social_talk_01", "social_story_01"}),
}
FILTER_COMPATIBILITY_VERSION = "explicit-exclusions-merged-activities-v1"

CHILD_ACTIVITY_INTRO_TEXT = 'Elegí una actividad que te guste. Leé qué necesitás y buscá esas cosas. Después mirá los pasos y dejá el celular a un lado para jugar. Si lo usás para poner música, dejalo apoyado. Podés volver a leer la consigna cuando lo necesites. Si ahora no tenés ganas, podés seguir sin elegir.'

def _expand_merged_activity_exclusions(activity_ids):
    """Conserva exclusiones explícitas sin deducir restricciones de una condición."""
    result = list(dict.fromkeys(activity_ids))
    for merged_id, predecessors in ACTIVITY_MERGE_PREDECESSORS.items():
        if predecessors.intersection(result) and merged_id not in result:
            result.append(merged_id)
    return tuple(result)
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
