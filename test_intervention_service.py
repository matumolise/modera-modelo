from intervention_engine import (
    request_voluntary_intervention,
)

from intervention_history import (
    RESPONSE_SELECTED,
    RESPONSE_POSTPONED,
)

from intervention_service import (
    register_intervention_response,
)


# ============================================================
# CASO 1
# Niño pide una actividad y selecciona una.
# ============================================================

decision = request_voluntary_intervention(
    interests=[
        "drawing",
        "sports",
    ],
    random_seed=42,
)

selected_activity = decision.activities[0]

record = register_intervention_response(
    child_id=1,
    decision=decision,
    response=RESPONSE_SELECTED,
    selected_activity_id=(
        selected_activity.activity_id
    ),
)

print("\nFLUJO COMPLETO - ACTIVIDAD SELECCIONADA\n")

print(
    f"Intervención generada: "
    f"{decision.should_intervene}"
)

print("Actividades ofrecidas:")

for activity in decision.activities:
    print(
        f"- {activity.title}"
    )

print(
    f"Respuesta: {record.response}"
)

print(
    "Actividad elegida: "
    f"{record.selected_activity_id}"
)

print(
    "Registro persistido: OK"
)


# ============================================================
# CASO 2
# Niño decide posponer.
# ============================================================

decision_2 = request_voluntary_intervention(
    random_seed=10,
)

record_2 = register_intervention_response(
    child_id=1,
    decision=decision_2,
    response=RESPONSE_POSTPONED,
)

print("\nFLUJO COMPLETO - INTERVENCIÓN POSPUESTA\n")

print(
    f"Respuesta: {record_2.response}"
)

print(
    "Actividad elegida: "
    f"{record_2.selected_activity_id}"
)

print(
    "Registro persistido: OK"
)

from datetime import datetime

from intervention_engine import (
    evaluate_bedtime_intervention,
)

from intervention_history import (
    RESPONSE_REJECTED,
)


# ============================================================
# CASO 3
# Intervención automática previa al sueño.
# ============================================================

bedtime_decision = evaluate_bedtime_intervention(
    current_time=datetime(
        2026,
        8,
        18,
        21,
        20,
    ),
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=True,
    interests=[
        "drawing",
    ],
    random_seed=42,
)

bedtime_record = register_intervention_response(
    child_id=1,
    decision=bedtime_decision,
    response=RESPONSE_REJECTED,
)

print(
    "\nFLUJO COMPLETO - INTERVENCIÓN BEDTIME\n"
)

print(
    f"Intervención generada: "
    f"{bedtime_decision.should_intervene}"
)

print(
    f"Origen: "
    f"{bedtime_decision.source}"
)

print(
    f"Contexto: "
    f"{bedtime_decision.context}"
)

print(
    "Actividades ofrecidas:"
)

for activity in bedtime_decision.activities:
    print(
        f"- {activity.title}"
    )

print(
    f"Respuesta: "
    f"{bedtime_record.response}"
)

print(
    f"Actividad elegida: "
    f"{bedtime_record.selected_activity_id}"
)

print(
    "Registro persistido: OK"
)
# CASO: oferta y respuesta vinculadas, persistidas en orden.
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from intervention_history import (
    append_intervention_offer,
    append_intervention_record,
)
from intervention_service import (
    create_offer_from_decision,
    register_offer_response,
)

traceable_decision = request_voluntary_intervention(random_seed=42)
offer = create_offer_from_decision(
    child_id=1,
    decision=traceable_decision,
    persist=False,
)
linked_response = register_offer_response(
    offer=offer,
    response=RESPONSE_POSTPONED,
    persist=False,
)

assert linked_response.offer_id == offer.offer_id
assert linked_response.activities_offered == offer.activities_offered

with TemporaryDirectory() as directory:
    history_path = str(Path(directory) / "history.jsonl")
    append_intervention_offer(offer, output_path=history_path)
    append_intervention_record(linked_response, output_path=history_path)
    events = [
        json.loads(line)
        for line in Path(history_path).read_text(encoding="utf-8").splitlines()
    ]

assert [event["event_type"] for event in events] == ["offer", "response"]
assert events[0]["offer_id"] == events[1]["offer_id"] == offer.offer_id
