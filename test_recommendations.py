from recommendations import (
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