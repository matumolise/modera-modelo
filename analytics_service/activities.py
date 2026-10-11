"""Adaptador puro del catálogo publicado; no crea ofertas ni aprende preferencias."""

import hashlib
import inspect
import json
from dataclasses import asdict

from recommendations import ACTIVITY_CATALOG, ActivityEligibility, recommend_activities


class InvalidSelection(ValueError):
    pass


CATALOG_SNAPSHOT = [asdict(activity) for activity in ACTIVITY_CATALOG]
CATALOG_VERSION = "provisional-sha256:" + hashlib.sha256(
    json.dumps(CATALOG_SNAPSHOT, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
).hexdigest()
ACTIVITY_IDS = frozenset(a.activity_id for a in ACTIVITY_CATALOG)
CATEGORIES = frozenset(a.category for a in ACTIVITY_CATALOG)
INTERESTS = frozenset(tag for a in ACTIVITY_CATALOG for tag in a.interest_tags)
SELECTOR_VERSION = "published-selector-sha256:" + hashlib.sha256(
    inspect.getsource(recommend_activities).encode()
).hexdigest()
LEVELS = frozenset({"calm", "moderate", "active"})
ELIGIBILITY_FIELDS = frozenset({
    "excluded_activity_ids", "excluded_categories", "allowed_activity_levels",
    "allow_requires_other_person", "allow_may_require_device_interaction",
})


def _string_list(value, vocabulary):
    if (not isinstance(value, list) or len(value) > 128
            or any(not isinstance(x, str) or x not in vocabulary for x in value)):
        raise InvalidSelection("Lista o vocabulario inválido")
    return tuple(sorted(set(value)))


def select_activities(request):
    allowed = {"request_id", "context", "interests", "recently_shown_ids", "eligibility", "eligibility_state"}
    if not isinstance(request, dict) or set(request) - allowed:
        raise InvalidSelection("Campos no admitidos")
    request_id = request.get("request_id")
    if (not isinstance(request_id, str) or not 1 <= len(request_id) <= 128
            or not request_id.isascii()
            or any(not (c.isalnum() or c in "_-.") for c in request_id)):
        raise InvalidSelection("request_id inválido")
    context = request.get("context")
    if not isinstance(context, str) or context not in {"voluntary", "general", "bedtime"}:
        raise InvalidSelection("Contexto inválido")
    interests = _string_list(request.get("interests", []), INTERESTS)
    recent = _string_list(request.get("recently_shown_ids", []), ACTIVITY_IDS)
    state = request.get("eligibility_state")
    if not isinstance(state, str) or state not in {"known", "unknown"}:
        raise InvalidSelection("Estado de elegibilidad requerido")
    if state == "unknown":
        if "eligibility" in request:
            raise InvalidSelection("Elegibilidad desconocida no admite filtros")
        return {
            "status": "unavailable", "reason": "eligibility_unknown",
            "request_id": request_id, "catalog_version": CATALOG_VERSION,
            "selector_version": SELECTOR_VERSION,
            "catalog_status": "PROVISIONAL", "activities": [],
        }
    if "eligibility" not in request:
        raise InvalidSelection("Elegibilidad conocida requiere filtros explícitos")
    fields = request["eligibility"]
    if not isinstance(fields, dict) or set(fields) - ELIGIBILITY_FIELDS:
        raise InvalidSelection("Elegibilidad no admitida")
    ids = _string_list(fields.get("excluded_activity_ids", []), ACTIVITY_IDS)
    categories = _string_list(fields.get("excluded_categories", []), CATEGORIES)
    levels = _string_list(fields.get("allowed_activity_levels", sorted(LEVELS)), LEVELS)
    other = fields.get("allow_requires_other_person", True)
    device = fields.get("allow_may_require_device_interaction", True)
    if type(other) is not bool or type(device) is not bool:
        raise InvalidSelection("Elegibilidad requiere booleanos")
    eligibility = ActivityEligibility(ids, categories, levels, other, device)
    canonical = {
        "request_id": request_id, "context": context, "interests": interests,
        "recently_shown_ids": recent, "eligibility": asdict(eligibility),
        "catalog_version": CATALOG_VERSION,
        "selector_version": SELECTOR_VERSION,
    }
    fingerprint = hashlib.sha256(json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    activities = recommend_activities(
        context=context, interests=interests, recently_shown_ids=recent,
        eligibility=eligibility, n=3, random_seed=int(fingerprint, 16),
    )
    return {
        "status": "selected" if activities else "no_eligible_activities",
        "request_id": request_id, "selection_fingerprint": fingerprint,
        "catalog_version": CATALOG_VERSION, "catalog_status": "PROVISIONAL",
        "selector_version": SELECTOR_VERSION,
        "activities": [asdict(a) for a in activities],
    }
