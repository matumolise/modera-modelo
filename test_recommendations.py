from recommendations import (
    ActivityEligibility,
    CONTEXT_BEDTIME,
    CONTEXT_VOLUNTARY,
    recommend_activities,
)


def print_recommendations(
    title,
    recommendations,
):
    print(f"\n{title}\n")

    for index, activity in enumerate(
        recommendations,
        start=1,
    ):
        print(
            f"{index}. {activity.title}"
        )

        print(
            f"   {activity.description}"
        )

        print(
            f"   categoría={activity.category}"
        )


# ============================================================
# CASO 1
# Actividad voluntaria sin intereses conocidos.
# ============================================================

voluntary = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    random_seed=42,
)

print_recommendations(
    "ACTIVIDADES VOLUNTARIAS",
    voluntary,
)


# ============================================================
# CASO 2
# Intereses opcionales.
# ============================================================

with_interests = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    interests=[
        "drawing",
        "sports",
    ],
    random_seed=42,
)

print_recommendations(
    "ACTIVIDADES CON INTERESES",
    with_interests,
)


# ============================================================
# CASO 3
# Bedtime.
# ============================================================

bedtime = recommend_activities(
    context=CONTEXT_BEDTIME,
    interests=[
        "drawing",
    ],
    random_seed=42,
)

print_recommendations(
    "ACTIVIDADES BEDTIME",
    bedtime,
)


# ============================================================
# CASO 4
# Penalización por repetición reciente.
# ============================================================

recent_ids = [
    activity.activity_id
    for activity in with_interests
]

after_recent = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    interests=[
        "drawing",
        "sports",
    ],
    recently_shown_ids=recent_ids,
    random_seed=42,
)

print_recommendations(
    "ACTIVIDADES DESPUÉS DE EVITAR REPETICIÓN",
    after_recent,
)
# ============================================================
# CASO 5
# Elegibilidad funcional antes del ranking.
# ============================================================

without_device_or_other_person = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    eligibility=ActivityEligibility(
        allow_requires_other_person=False,
        allow_may_require_device_interaction=False,
    ),
    random_seed=42,
)

assert all(
    not activity.requires_other_person
    for activity in without_device_or_other_person
)

assert all(
    not activity.may_require_device_interaction
    for activity in without_device_or_other_person
)


# ============================================================
# CASO 6
# Puede devolver menos de n o ninguna actividad.
# ============================================================

no_activities = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    eligibility=ActivityEligibility(
        excluded_categories=(
            "movement",
            "creative",
            "reading",
            "free_play",
            "social_family",
        ),
    ),
)

assert no_activities == []
