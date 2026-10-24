"""Adaptación HTTP del coordinador existente, sin reglas de oferta adicionales."""

from dataclasses import fields
import sqlite3
from .pmum import ModelUnavailable

from .child_offers import (
    ChildOfferCoordinator, CoordinatorConflict, CoordinatorUnavailable,
    OfferEvidence, POLICY, _identifier,
)


COORDINATOR_API_VERSION = "child-offers-http-v1"
ADAPTIVE_API_VERSION = "child-offers-http-v2-pmum-candidate"


def parse_adaptive_evaluation(payload):
    if not isinstance(payload, dict) or set(payload) != {"request_id", "evidence", "pmum_parent_answers"}:
        raise ValueError("Invalid adaptive evaluation envelope")
    answers = payload["pmum_parent_answers"]
    if answers is not None and not isinstance(answers, dict):
        raise ValueError("Parent answers must be an object or null")
    request_id, evidence = parse_evaluation({key: payload[key] for key in ("request_id", "evidence")})
    return request_id, evidence, answers


def parse_evaluation(payload):
    if not isinstance(payload, dict) or set(payload) != {"request_id", "evidence"}:
        raise ValueError("Invalid evaluation envelope")
    _identifier(payload["request_id"])
    evidence = payload["evidence"]
    required = {field.name for field in fields(OfferEvidence)} - {"eligibility", "interests"}
    allowed = {field.name for field in fields(OfferEvidence)}
    if not isinstance(evidence, dict) or not required <= set(evidence) <= allowed:
        raise ValueError("Invalid evidence fields")
    for key in ("now", "interval_started_at", "bedtime_at", "eligibility_state"):
        if not isinstance(evidence[key], str):
            raise ValueError("Evidence text fields must be strings")
    interests = evidence.get("interests", [])
    if not isinstance(interests, list):
        raise ValueError("Interests must be a JSON list")
    return payload["request_id"], OfferEvidence(**{**evidence, "interests": tuple(interests)})


def parse_event(payload):
    required = {"request_id", "profile_id", "offer_id", "event", "occurred_at", "now"}
    allowed = required | {"channel", "selected_activity_id"}
    if not isinstance(payload, dict) or not required <= set(payload) <= allowed:
        raise ValueError("Invalid event fields")
    for key in required:
        if not isinstance(payload[key], str):
            raise ValueError("Event fields must be strings")
    for key in ("request_id", "profile_id", "offer_id"):
        _identifier(payload[key])
    for key in ("channel", "selected_activity_id"):
        if payload.get(key) is not None and not isinstance(payload[key], str):
            raise ValueError("Optional event fields must be strings or null")
    return payload["request_id"], {key: value for key, value in payload.items() if key != "request_id"}


class ChildOfferRuntime:
    """Reabre una base inicializada y conserva las transacciones del coordinador."""

    def __init__(self, path, *, policy=None, pmum=None):
        self.coordinator = ChildOfferCoordinator(path, policy=policy)
        self.pmum = pmum

    def check_ready(self):
        try:
            # Consultar un perfil ausente no crea perfiles, recibos ni eventos.
            self.coordinator.history("health-probe")
            return True
        except (sqlite3.Error, OSError, ValueError):
            return False

    def _call(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (sqlite3.Error, OSError) as error:
            raise CoordinatorUnavailable("Coordinator storage unavailable") from error

    def evaluate(self, request_id, evidence):
        return self._call(self.coordinator.evaluate, request_id, evidence)

    def evaluate_adaptive(self, request_id, evidence, parent_answers):
        def estimate(answers):
            if self.pmum is None:
                raise ModelUnavailable("El estimador no está configurado")
            result = self.pmum.estimate(answers)
            if result.get("status") == "estimated":
                result = {**result, "artifact_sha256": self.pmum.artifact_sha256}
            return result
        return self._call(self.coordinator.evaluate, request_id, evidence,
                          parent_answers=parent_answers, estimator=estimate)

    def record_event(self, request_id, payload):
        return self._call(self.coordinator.record_event, request_id, **payload)

    def history(self, profile_id):
        return self._call(self.coordinator.history, profile_id)
