"""Contrato HTTP con evidencia ficticia controlada, sin captura ni familias reales."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from analytics_service.child_offers import ChildOfferCoordinator, CoordinatorUnavailable
from analytics_service.http import create_app
from analytics_service.settings import Settings


TOKEN = "fictitious-integration-token-0001"
HEADERS = {"Authorization": "Bearer " + TOKEN}
ROOT = Path(__file__).resolve().parents[1]
EVALUATE = "/v1/child-offers/evaluate"
EVENTS = "/v1/child-offers/events"
PROFILE = "fictitious-account.child-001"
HISTORY = "/v1/child-offers/profiles/" + PROFILE + "/history"


def evaluation():
    return json.loads((ROOT / "tests/fixtures/integration/child_offer_evaluation_fictitious.json").read_text(encoding="utf-8"))


def event(offer, name="delivered", request_id="fictitious-delivery-001", **changes):
    result = {"request_id": request_id, "profile_id": PROFILE, "offer_id": offer["offer_id"],
              "event": name, "occurred_at": "2026-10-16T10:00:00-03:00", "now": "2026-10-16T10:00:00-03:00"}
    if name == "delivered":
        result["channel"] = "overlay"
    return {**result, **changes}


@pytest.fixture
def settings(tmp_path):
    path = tmp_path / "fictitious-child-offers.sqlite"
    ChildOfferCoordinator(path, create=True)
    return Settings(token=TOKEN, child_offers_enabled=True, child_offers_repository_path=path)


def test_restart_preserves_original_evaluation_event_and_current_history(settings):
    payload = evaluation()
    with TestClient(create_app(settings)) as client:
        opened = client.post(EVALUATE, json=payload, headers=HEADERS)
        assert opened.status_code == 200
        original = opened.json()
        assert original["offer"]["delivered_at"] is None
        delivery = event(original["offer"])
        delivered = client.post(EVENTS, json=delivery, headers=HEADERS).json()
        selected_payload = event(original["offer"], "selected", "fictitious-response-001",
                                 selected_activity_id=original["offer"]["activities_offered"][0])
        selected = client.post(EVENTS, json=selected_payload, headers=HEADERS)
        assert selected.status_code == 200
        assert selected.json()["offer"]["response"] == "selected"
        assert client.get(HISTORY, headers=HEADERS).json()["offers"][0]["status"] == "responded"
    with TestClient(create_app(settings)) as client:
        assert client.post(EVALUATE, json=payload, headers=HEADERS).json() == {**original, "replayed": True}
        assert client.post(EVENTS, json=delivery, headers=HEADERS).json() == {**delivered, "replayed": True}
        assert client.post(EVENTS, json=selected_payload, headers=HEADERS).json() == {**selected.json(), "replayed": True}
        history = client.get(HISTORY, headers=HEADERS).json()
        assert len(history["offers"]) == 1
        assert len(history["events"]) == 3
        assert history["offers"][0]["status"] == "responded"
        assert opened.headers["cache-control"] == "no-store"


def test_http_delegates_same_policy_and_selection_as_library(settings, tmp_path, monkeypatch):
    from analytics_service.child_offer_api import parse_evaluation
    monkeypatch.setattr("analytics_service.child_offers.uuid4", lambda: "fictitious-fixed-offer")
    payload = evaluation()
    request_id, evidence = parse_evaluation(payload)
    direct = ChildOfferCoordinator(tmp_path / "direct.sqlite", create=True).evaluate(request_id, evidence)
    with TestClient(create_app(settings)) as client:
        assert client.post(EVALUATE, json=payload, headers=HEADERS).json() == direct


@pytest.mark.parametrize("change", [
    {"automatic_enabled": False}, {"assignment_verified": False}, {"capture_verified": False},
    {"shared_phone": True}, {"screen_interactive": False}, {"in_school_period": True},
    {"eligibility_state": "unknown", "eligibility": None},
])
def test_untrusted_or_insufficient_evidence_suppresses_without_delivery(settings, change):
    payload = evaluation()
    payload["evidence"].update(change)
    with TestClient(create_app(settings)) as client:
        response = client.post(EVALUATE, json=payload, headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["status"] == "suppressed"
        assert client.get(HISTORY, headers=HEADERS).json()["offers"] == []


@pytest.mark.parametrize("payload", [
    None, [], {}, {"request_id": "fictitious-eval"},
    {**evaluation(), "unexpected": True},
    {**evaluation(), "request_id": 1},
    {**evaluation(), "evidence": None},
    {**evaluation(), "evidence": {**evaluation()["evidence"], "interests": "movement"}},
    {**evaluation(), "evidence": {**evaluation()["evidence"], "capture_verified": 1}},
    {**evaluation(), "evidence": {**evaluation()["evidence"], "now": 123}},
    {**evaluation(), "evidence": {**evaluation()["evidence"], "now": "2026-10-16T10:00:00"}},
    {**evaluation(), "evidence": {**evaluation()["evidence"], "extra": "rejected"}},
])
def test_malformed_evaluation_does_not_write_receipts(settings, payload):
    with TestClient(create_app(settings)) as client:
        response = client.post(EVALUATE, content=json.dumps(payload), headers={**HEADERS, "Content-Type": "application/json"})
        assert response.status_code == 400
    with sqlite3.connect(settings.child_offers_repository_path) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 0


def test_conflicts_do_not_duplicate_offers_or_change_history(settings):
    payload = evaluation()
    with TestClient(create_app(settings)) as client:
        original = client.post(EVALUATE, json=payload, headers=HEADERS).json()
        altered = deepcopy(payload)
        altered["evidence"]["game_active"] = True
        assert client.post(EVALUATE, json=altered, headers=HEADERS).status_code == 409
        # Una selección no puede preceder al acuse de entrega.
        selected = event(original["offer"], "selected", "fictitious-selection",
                         selected_activity_id=original["offer"]["activities_offered"][0])
        assert client.post(EVENTS, json=selected, headers=HEADERS).status_code == 409
        history = client.get(HISTORY, headers=HEADERS).json()
        assert len(history["offers"]) == 1
        assert len(history["events"]) == 1


def test_global_request_identity_across_profiles_and_operations(settings):
    with TestClient(create_app(settings)) as client:
        payload = evaluation()
        offer = client.post(EVALUATE, json=payload, headers=HEADERS).json()["offer"]
        other = deepcopy(payload)
        other["evidence"]["profile_id"] = "fictitious-other-profile"
        assert client.post(EVALUATE, json=other, headers=HEADERS).status_code == 409
        assert client.post(EVENTS, json=event(offer, request_id=payload["request_id"]), headers=HEADERS).status_code == 409


def test_expired_replay_is_not_a_new_delivery_permission(settings):
    payload = evaluation()
    with TestClient(create_app(settings)) as client:
        original = client.post(EVALUATE, json=payload, headers=HEADERS).json()
        fresh = deepcopy(payload)
        fresh["request_id"] = "fictitious-later-evaluation"
        fresh["evidence"]["now"] = "2026-10-16T10:11:00-03:00"
        assert client.post(EVALUATE, json=fresh, headers=HEADERS).json()["reason"] == "delivery_reconciliation_required"
        replay = client.post(EVALUATE, json=payload, headers=HEADERS).json()
        assert replay == {**original, "replayed": True}
        assert client.get(HISTORY, headers=HEADERS).json()["offers"][0]["status"] == "delivery_unknown"


def test_storage_loss_reports_unavailable_without_reinitializing(settings):
    with TestClient(create_app(settings)) as client:
        settings.child_offers_repository_path.unlink()
        assert client.get("/health/live").status_code == 200
        assert client.get("/health").status_code == 503
        assert client.post(EVALUATE, json=evaluation(), headers=HEADERS).status_code == 503
        assert client.get(HISTORY, headers=HEADERS).status_code == 503
        assert not settings.child_offers_repository_path.exists()


def test_receipt_loss_reports_unavailable(settings):
    with TestClient(create_app(settings)) as client:
        client.post(EVALUATE, json=evaluation(), headers=HEADERS)
        with sqlite3.connect(settings.child_offers_repository_path) as db:
            db.execute("DELETE FROM receipts")
        assert client.get("/health").status_code == 503
        assert client.post(EVALUATE, json=evaluation(), headers=HEADERS).status_code == 503


def test_readiness_and_history_are_read_only(settings):
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            assert client.get("/health").status_code == 200
            assert client.get(HISTORY, headers=HEADERS).json() == {"offers": [], "events": []}
    with sqlite3.connect(settings.child_offers_repository_path) as db:
        state = json.loads(db.execute("SELECT body FROM state WHERE id=1").fetchone()[0])
        assert state["profiles"] == {}
        assert state["receipt_count"] == 0


def test_transport_auth_validation_and_no_store(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post(EVALUATE, content="x" * 20000).status_code == 401
        assert client.post(EVALUATE, content="x" * 20000, headers=HEADERS).status_code == 413
        assert client.post(EVALUATE, content="{}", headers=HEADERS).status_code == 415
        response = client.post(EVALUATE, content='{"request_id":"a","request_id":"b"}', headers={**HEADERS, "Content-Type": "application/json"})
        assert response.status_code == 400
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/v1/child-offers/profiles/bad!profile/history", headers=HEADERS).status_code == 400


def test_disabled_capability_and_explicit_initialization(settings, tmp_path):
    with TestClient(create_app(Settings(token=TOKEN))) as client:
        assert client.post(EVALUATE, json=evaluation(), headers=HEADERS).status_code == 503
        assert client.post(EVENTS, json={}, headers=HEADERS).status_code == 503
        assert client.get(HISTORY, headers=HEADERS).status_code == 503
    missing = replace(settings, child_offers_repository_path=tmp_path / "missing.sqlite")
    with pytest.raises(CoordinatorUnavailable):
        with TestClient(create_app(missing)):
            pass
    assert not missing.child_offers_repository_path.exists()


def test_settings_require_distinct_absolute_storage(settings, monkeypatch):
    with pytest.raises(ValueError):
        replace(settings, child_offers_repository_path=Path("relative.sqlite"))
    with pytest.raises(ValueError):
        replace(settings, adult_messages_repository_path=settings.child_offers_repository_path)
    monkeypatch.setenv("ANALYTICS_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ANALYTICS_CHILD_OFFERS_ENABLED", "true")
    monkeypatch.setenv("ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH", str(settings.child_offers_repository_path))
    assert Settings.from_env().child_offers_repository_path == settings.child_offers_repository_path
