from recommendations import (
    CONTEXT_VOLUNTARY,
    recommend_activities,
)

from intervention_history import (
    RESPONSE_SELECTED,
    create_intervention_record,
    append_intervention_record,
)

from intervention_history import SOURCE_CHILD_INITIATED


activities = recommend_activities(
    context=CONTEXT_VOLUNTARY,
    interests=[
        "drawing",
        "sports",
    ],
    random_seed=42,
)

activity_ids = [
    activity.activity_id
    for activity in activities
]

selected = activities[0]

record = create_intervention_record(
    child_id=1,
    source=SOURCE_CHILD_INITIATED,
    context=CONTEXT_VOLUNTARY,
    activities_offered=activity_ids,
    response=RESPONSE_SELECTED,
    selected_activity_id=selected.activity_id,
)

append_intervention_record(
    record
)

print("\nREGISTRO DE INTERVENCIÓN\n")

print(
    f"Niño: {record.child_id}"
)

print(
    f"Origen: {record.source}"
)

print(
    f"Contexto: {record.context}"
)

print(
    "Actividades ofrecidas:"
)

for activity in activities:
    print(
        f"- {activity.activity_id}"
    )

print(
    f"Respuesta: {record.response}"
)

print(
    "Actividad seleccionada: "
    f"{record.selected_activity_id}"
)

print(
    "\nRegistro guardado: OK"
)