"""Formulario candidato: no deduce capacidades ni seguridad de una etiqueta."""

from .activities import CATALOG_VERSION, InvalidSelection

MAPPING_VERSION = "considerations-resolution-v1-candidate"
DOMAINS = {
    "mobility_arms_hands": ("manual_tasks",),
    "mobility_legs": ("leg_movement",),
    "mobility_both": ("manual_tasks", "leg_movement"),
    "visual": ("visual_material", "instruction_access"),
    "auditory": ("listening", "communication_mode"),
    "sensory": ("specific_stimuli",),
}
QUESTIONS = {
    "manual_tasks": "¿Qué tareas de dibujo o manipulación conviene evitar o adaptar?",
    "leg_movement": "¿Qué movimientos o desplazamientos conviene evitar o adaptar?",
    "visual_material": "¿Qué apoyo hace falta para libros, dibujos u objetos visuales?",
    "instruction_access": "¿Cómo debe presentarse la consigna para que sea accesible?",
    "listening": "¿Hay que evitar o adaptar música e historias escuchadas?",
    "communication_mode": "¿Qué forma de comunicación resulta accesible?",
    "specific_stimuli": "¿Qué estímulos concretos se deben evitar y en qué contexto?",
}


def resolve_considerations(request):
    if not isinstance(request, dict) or set(request) - {
        "request_id", "considerations_state", "conditions"
    }:
        raise InvalidSelection("Campos de consideraciones no admitidos")
    request_id = request.get("request_id")
    if (not isinstance(request_id, str) or not 1 <= len(request_id) <= 128
            or not request_id.isascii()
            or any(not (c.isalnum() or c in "_-.") for c in request_id)):
        raise InvalidSelection("request_id invalido")
    state = request.get("considerations_state")
    common = {"request_id": request_id, "mapping_version": MAPPING_VERSION,
              "catalog_version": CATALOG_VERSION, "catalog_status": "PROVISIONAL"}
    if state == "unknown":
        if "conditions" in request:
            raise InvalidSelection("Estado desconocido no admite condiciones")
        return {**common, "eligibility_state": "unknown", "reason": "considerations_unknown",
                "required_followups": []}
    conditions = request.get("conditions")
    if (state != "known" or not isinstance(conditions, list) or not conditions
            or len(conditions) > 6
            or any(not isinstance(c, str) or c not in {*DOMAINS, "none"} for c in conditions)
            or len(set(conditions)) != len(conditions)):
        raise InvalidSelection("Seleccion explicita y valida requerida")
    if "none" in conditions:
        if conditions != ["none"]:
            raise InvalidSelection("Ninguna es exclusiva")
        return {**common, "eligibility_state": "known", "eligibility": {},
                "required_followups": []}
    if sum(c.startswith("mobility_") for c in conditions) > 1:
        raise InvalidSelection("Elegir una sola opcion de movilidad")
    domains = sorted({domain for c in conditions for domain in DOMAINS[c]})
    return {**common, "eligibility_state": "unknown", "reason": "functional_mapping_required",
            "required_followups": [{"domain": d, "question": QUESTIONS[d]} for d in domains]}
