from datetime import datetime, timedelta

from intervention_engine import (
    request_voluntary_intervention,
    evaluate_bedtime_intervention,
)


def print_decision(
    title,
    decision,
):
    print(f"\n{title}\n")

    print(
        f"Intervenir: "
        f"{decision.should_intervene}"
    )

    print(
        f"Motivo: "
        f"{decision.reason}"
    )

    if decision.should_intervene:

        print(
            f"Origen: "
            f"{decision.source}"
        )

        print(
            f"Contexto: "
            f"{decision.context}"
        )

        print(
            "Actividades:"
        )

        for activity in decision.activities:
            print(
                f"- {activity.title}"
            )


# ============================================================
# CASO 1
# El niño pide voluntariamente una actividad.
# ============================================================

voluntary = request_voluntary_intervention(
    interests=[
        "drawing",
        "sports",
    ],
    random_seed=42,
)

print_decision(
    "CASO 1 - SOLICITUD VOLUNTARIA",
    voluntary,
)


# ============================================================
# CASO 2
# Faltan 40 minutos para dormir.
# El dispositivo está siendo usado.
# ============================================================

current_time = datetime(
    2026,
    8,
    18,
    21,
    20,
)

bedtime = evaluate_bedtime_intervention(
    current_time=current_time,
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=True,
    interests=[
        "drawing",
    ],
    random_seed=42,
)

print_decision(
    "CASO 2 - BEDTIME ACTIVO",
    bedtime,
)


# ============================================================
# CASO 3
# Bedtime, pero acaba de recibir otra intervención.
# ============================================================

recent_bedtime_intervention = (
    current_time
    - timedelta(
        minutes=20
    )
)

cooldown = evaluate_bedtime_intervention(
    current_time=current_time,
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=True,
    last_bedtime_intervention=(
        recent_bedtime_intervention
    ),
    interests=[
        "drawing",
    ],
    random_seed=42,
)

print_decision(
    "CASO 3 - COOLDOWN ACTIVO",
    cooldown,
)


# ============================================================
# CASO 4
# Faltan más de 60 minutos para dormir.
# ============================================================

too_early = evaluate_bedtime_intervention(
    current_time=datetime(
        2026,
        8,
        18,
        20,
        30,
    ),
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=True,
    random_seed=42,
)

print_decision(
    "CASO 4 - FUERA DE VENTANA BEDTIME",
    too_early,
)


# ============================================================
# CASO 5
# Está dentro de la ventana, pero no está usando el teléfono.
# ============================================================

device_not_in_use = evaluate_bedtime_intervention(
    current_time=current_time,
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=False,
    random_seed=42,
)

print_decision(
    "CASO 5 - DISPOSITIVO SIN USO",
    device_not_in_use,
)

# ============================================================
# CASO 6
# El horario de sueño ya pasó.
# No debe generar otra intervención automática.
# ============================================================

after_bedtime = evaluate_bedtime_intervention(
    current_time=datetime(
        2026,
        8,
        18,
        22,
        20,
    ),
    bedtime_hour=22,
    bedtime_minute=0,
    device_in_use=True,
    random_seed=42,
)

print_decision(
    "CASO 6 - DESPUÉS DE BEDTIME",
    after_bedtime,
)