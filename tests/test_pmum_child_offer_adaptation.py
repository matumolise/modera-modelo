"""Integración controlada: el predictor de este archivo es ficticio, no Ridge."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
import joblib
import pytest

from analytics_service.child_offers import ChildOfferCoordinator, POLICY
from analytics_service.child_offer_timing import adaptive_policy, timing_from_estimate
from analytics_service.http import create_app
from analytics_service.migrate_child_offer_pmum import migrate
from analytics_service.pmum import ModelUnavailable
from analytics_service.settings import Settings
from experiments.hu_pmum_candidate_v1 import MODEL_VERSION, FEATURES, EXPECTED_SHA256
from tests.test_child_offer_coordinator import BASE, evidence, deliver, respond


TOKEN = "fictitious-adaptive-test-token"
HEADERS = {"Authorization": "Bearer " + TOKEN}
URL = "/v2/child-offers/evaluate"
V2 = adaptive_policy(POLICY, 120, 180)  # Extremos ficticios explícitos de ensayo.
ANSWERS = {"age": 9, "sex_code": 1, "weekday_category": 2,
           "weekend_category": 3, "respondent": "parent_or_caregiver", "reference_days": 30}


class ControlledPredictor:
    """Produce 1 o 5 para dos categorías; no es un modelo entrenado."""

    def predict(self, row):
        category = int(row[0][2])
        return [float(category) if category in {1, 5} else 2.6959]


def estimate(score):
    return {"status": "estimated", "estimated_pmum_sf_mean": score,
            "model_version": MODEL_VERSION, "artifact_sha256": "a" * 64,
            "experimental": True}


def evaluate(coordinator, request, data, score=3, **kw):
    return coordinator.evaluate(request, data, parent_answers={"controlled_score": score},
                                estimator=lambda _: estimate(score), **kw)


def settled(coordinator, score=3):
    first = evaluate(coordinator, "first", evidence(), score)
    deliver(coordinator, first, BASE)
    respond(coordinator, first, BASE)
    return first


@pytest.fixture
def coordinator(tmp_path):
    return ChildOfferCoordinator(tmp_path / "adaptive.sqlite", create=True, policy=V2)


@pytest.fixture
def settings(tmp_path):
    model = tmp_path / "controlled.joblib"
    joblib.dump({"model": ControlledPredictor(), "version": MODEL_VERSION,
                 "features": FEATURES, "source_sha256": EXPECTED_SHA256,
                 "trained_rows": 803, "sex_codes": [1, 2], "target": "PMUMTotal/9"}, model)
    source = Path(__file__).resolve().parents[1] / "docs/own_closure/evidence/pmum_2026-10-14/original_manifest_recovered.json"
    metadata = json.loads(source.read_text(encoding="utf-8"))
    metadata["evaluation"] = "Fixture de transporte; sin evaluación predictiva real"
    manifest = tmp_path / "controlled.json"
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    path = tmp_path / "adaptive.sqlite"
    ChildOfferCoordinator(path, create=True, policy=V2)
    return Settings(token=TOKEN, pmum_enabled=True, model_path=model, manifest_path=manifest,
                    model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                    child_offers_enabled=True, child_offers_repository_path=path,
                    child_offers_pmum_min_minutes=120, child_offers_pmum_max_minutes=180)


def payload(request="first", data=None, **answers):
    return {"request_id": request, "evidence": asdict(data or evidence()),
            "pmum_parent_answers": {**ANSWERS, **answers}}


def test_timing_is_continuous_monotone_bounded_and_not_a_risk_class():
    values = [timing_from_estimate(estimate(1 + i / 100), V2["pmum_timing"])
              for i in range(401)]
    waits = [v["cooldown_minutes"] for v in values]
    assert waits[0] == 180 and waits[-1] == 120
    assert all(a > b for a, b in zip(waits, waits[1:]))
    assert all(120 <= x <= 180 for x in waits)
    assert not any("risk" in key for v in values for key in v)


@pytest.mark.parametrize("score", [True, None, float("nan"), float("inf"), 0, 5.01, "3"])
def test_bad_estimates_cannot_create_timing(score):
    with pytest.raises(ValueError):
        timing_from_estimate(estimate(score), V2["pmum_timing"])


@pytest.mark.parametrize("low,high", [(90, 180), (120, 120), (180, 120), (120, None), (True, 180)])
def test_policy_requires_explicit_ordered_bounds_and_preserves_minimum(low, high):
    with pytest.raises(ValueError):
        adaptive_policy(POLICY, low, high)


def test_higher_score_allows_second_offer_earlier_without_changing_selection(tmp_path):
    results = []
    for score in (1, 5):
        c = ChildOfferCoordinator(tmp_path / f"score-{score}.sqlite", create=True, policy=V2)
        results.append(settled(c, score))
        result = evaluate(c, "after-150", evidence(BASE + timedelta(minutes=150), "second"), score)
        assert result["status"] == ("suppressed" if score == 1 else "offer")
        if score == 1:
            assert result["reason"] == "shared_cooldown"
    assert results[0]["offer"]["selection"] == results[1]["offer"]["selection"]


def test_current_answers_cannot_shorten_wait_started_with_previous_offer(coordinator):
    first = settled(coordinator, 1)
    data = evidence(BASE + timedelta(minutes=150), "second")
    assert evaluate(coordinator, "changed-answers", data, 5)["reason"] == "shared_cooldown"
    assert first["offer"]["timing"]["cooldown_minutes"] == 180
    at_boundary = evidence(BASE + timedelta(minutes=180), "third")
    assert evaluate(coordinator, "boundary", at_boundary, 5)["status"] == "offer"


def test_higher_score_cannot_bypass_continuity_quota_or_rejections(coordinator):
    short = evidence(interval="short-interval", interval_started_at=(BASE - timedelta(minutes=44)).isoformat())
    assert evaluate(coordinator, "short", short, 5)["reason"] == "outside_trigger"
    first = evaluate(coordinator, "first", evidence(), 5)
    deliver(coordinator, first, BASE)
    respond(coordinator, first, BASE, "rejected")
    at = BASE + timedelta(minutes=120)
    second = evaluate(coordinator, "second", evidence(at, "second"), 5)
    deliver(coordinator, second, at, "delivery-second")
    respond(coordinator, second, at, "rejected", "rejection-second")
    at += timedelta(minutes=120)
    assert evaluate(coordinator, "third", evidence(at, "third"), 5)["reason"] == "rejection_pause"


def test_daytime_quota_still_applies(coordinator):
    for i in range(2):
        at = BASE + timedelta(minutes=i * 120)
        result = evaluate(coordinator, f"eval-{i}", evidence(at, f"interval-{i}"), 5)
        deliver(coordinator, result, at, f"delivery-{i}")
        respond(coordinator, result, at, request=f"response-{i}")
    later = BASE + timedelta(minutes=240)
    assert evaluate(coordinator, "third", evidence(later, "third"), 5)["reason"] == "automatic_quota"


@pytest.mark.parametrize("changes,reason", [
    ({"capture_verified": False}, "capture_unverified"),
    ({"shared_phone": True}, "identity_uncertain"),
    ({"in_school_period": True}, "school_period"),
    ({"assignment_verified": False}, "identity_uncertain"),
    ({"automatic_enabled": False}, "automatic_disabled"),
    ({"screen_interactive": False}, "screen_inactive"),
    ({"eligibility_state": "unknown", "eligibility": None}, "eligibility_unknown"),
])
def test_model_does_not_override_capture_identity_or_school(coordinator, changes, reason):
    def forbidden(_):
        raise AssertionError("El estimador no debe utilizarse ante esta guarda")
    result = coordinator.evaluate("guard", evidence(**changes), parent_answers=ANSWERS, estimator=forbidden)
    assert result["status"] == "suppressed"
    assert result["reason"] == reason


def test_estimator_failure_rolls_back_and_can_retry(coordinator):
    def fail(_):
        raise ModelUnavailable("controlled failure")
    with pytest.raises(ModelUnavailable):
        coordinator.evaluate("first", evidence(), parent_answers=ANSWERS, estimator=fail)
    assert coordinator.history(evidence().profile_id) == {"offers": [], "events": []}
    with sqlite3.connect(coordinator.path) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 0
    assert coordinator.evaluate("first", evidence(), parent_answers=ANSWERS,
                                estimator=lambda _: estimate(3))["status"] == "offer"


def test_replay_after_restart_does_not_need_inference_and_conflicts_are_atomic(coordinator):
    original = evaluate(coordinator, "first", evidence(), 1)
    reopened = ChildOfferCoordinator(coordinator.path, policy=V2)
    def fail(_):
        raise AssertionError("Un replay no debe volver a inferir")
    replay = reopened.evaluate("first", evidence(), parent_answers={"controlled_score": 1}, estimator=fail)
    assert replay == {**original, "replayed": True}
    before = reopened.history(evidence().profile_id)
    with pytest.raises(ValueError, match="reused"):
        evaluate(reopened, "first", evidence(), 5)
    assert reopened.history(evidence().profile_id) == before


def test_concurrent_retry_has_one_offer_and_one_inference(coordinator):
    calls = []
    def predictor(_):
        calls.append(1)
        return estimate(3)
    def run(_):
        return coordinator.evaluate("same", evidence(), parent_answers=ANSWERS, estimator=predictor)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    assert len(calls) == 1
    assert sum(not r["replayed"] for r in results) == 1
    assert len({r["offer"]["offer_id"] for r in results}) == 1


def test_http_runs_cached_predictor_then_coordinates_and_replays_after_restart(settings):
    request = payload(weekday_category=5)
    with TestClient(create_app(settings)) as client:
        response = client.post(URL, json=request, headers=HEADERS)
        assert response.status_code == 200
        original = response.json()
        timing = original["offer"]["timing"]
        assert timing["estimated_pmum_sf_mean"] == 5
        assert timing["cooldown_minutes"] == 120
        assert timing["artifact_sha256"] == settings.model_sha256
        assert "pmum_parent_answers" not in original["offer"]["evidence"]
        assert client.get("/health").json()["capabilities"]["child_offers"]["pmum_timing"] == V2["pmum_timing"]
        # La ruta anterior no permite generar ofertas nuevas sin estimación.
        v1 = {k: v for k, v in payload("bypass").items() if k != "pmum_parent_answers"}
        assert client.post("/v1/child-offers/evaluate", json=v1, headers=HEADERS).status_code == 400
    with TestClient(create_app(settings)) as client:
        client.app.state.pmum.ready = False
        assert client.post(URL, json=request, headers=HEADERS).json() == {**original, "replayed": True}


@pytest.mark.parametrize("answer_changes,reason", [
    ({"weekday_category": None}, "missing_parent_answer"),
    ({"age": 5}, "invalid_feature_value"),
    ({"sex_code": 4}, "invalid_feature_value"),
    ({"reference_days": 7}, "reference_period_mismatch"),
    ({"respondent": "android"}, "respondent_mismatch"),
])
def test_missing_or_incompatible_parent_inputs_suppress_without_fabricating_score(settings, answer_changes, reason):
    with TestClient(create_app(settings)) as client:
        result = client.post(URL, json=payload(**answer_changes), headers=HEADERS).json()
        assert result == {"status": "suppressed", "reason": "pmum_unavailable", "pmum_reason": reason,
                          "policy_version": V2["version"], "replayed": False}
        assert client.app.state.child_offers.history(evidence().profile_id)["offers"] == []


def test_http_does_not_accept_a_score_from_android_or_backend(settings):
    with TestClient(create_app(settings)) as client:
        request = payload()
        request["estimated_pmum_sf_mean"] = 5
        assert client.post(URL, json=request, headers=HEADERS).status_code == 400
        request = payload()
        request["evidence"]["estimated_pmum_sf_mean"] = 5
        assert client.post(URL, json=request, headers=HEADERS).status_code == 400


def test_existing_database_requires_explicit_copy_and_preserves_history_receipts(tmp_path):
    source = tmp_path / "legacy.sqlite"
    old = ChildOfferCoordinator(source, create=True)
    first = old.evaluate("legacy", evidence())
    deliver(old, first, BASE)
    respond(old, first, BASE)
    original_bytes = source.read_bytes()
    original_history = old.history(evidence().profile_id)
    with pytest.raises(ValueError, match="mismatch"):
        ChildOfferCoordinator(source, policy=V2)
    target = tmp_path / "adaptive.sqlite"
    result = migrate(source, target, 120, 180)
    assert result["legacy_receipts_preserved"] == 3
    assert source.read_bytes() == original_bytes
    new = ChildOfferCoordinator(target, policy=V2)
    assert new.history(evidence().profile_id) == original_history
    assert new.evaluate("legacy", evidence()) == {**first, "replayed": True}
    assert evaluate(new, "new", evidence(BASE + timedelta(minutes=120), "new"), 1)["status"] == "offer"
    with pytest.raises(FileExistsError):
        migrate(source, target, 120, 180)


def test_adaptation_must_be_enabled_explicitly_and_cannot_start_without_model(settings):
    with TestClient(create_app(Settings(token=TOKEN))) as client:
        assert client.post(URL, json=payload(), headers=HEADERS).status_code == 503
    with pytest.raises(ValueError, match="PMUM"):
        replace(settings, pmum_enabled=False)
    with pytest.raises(ModelUnavailable):
        with TestClient(create_app(replace(settings, model_sha256="0" * 64))):
            pass
    with pytest.raises(ValueError):
        replace(settings, child_offers_pmum_max_minutes=None)


def test_real_process_http_restart_and_six_receipts_with_controlled_predictor(settings, tmp_path):
    from tools.validation.verify_pmum_child_offer_integration import verify
    directory = tmp_path / "controlled-model"
    directory.mkdir()
    shutil.copyfile(settings.model_path, directory / (MODEL_VERSION + ".joblib"))
    shutil.copyfile(settings.manifest_path, directory / (MODEL_VERSION + ".json"))
    result = verify(directory, tmp_path / "real-process", 120, 180,
                    expected_sha256=settings.model_sha256)
    assert result["status"] == "PASS"
    assert result["original_registered_model"] is False
    assert result["replayed_original_receipts"] == 6
    assert result["model_files_unchanged"] is True
    assert result["real_android_backend_aws_validated"] is False


def test_policy_cannot_be_changed_by_boolean_numeric_equality(tmp_path):
    invalid = deepcopy(POLICY)
    invalid["maximum_bedtime"] = True
    with pytest.raises(ValueError):
        ChildOfferCoordinator(tmp_path / "invalid.sqlite", create=True, policy=invalid)


def test_environment_requires_explicit_bounds(settings, monkeypatch):
    for key, value in {
        "ANALYTICS_SERVICE_TOKEN": TOKEN, "ANALYTICS_PMUM_ENABLED": "true",
        "ANALYTICS_MODEL_PATH": str(settings.model_path),
        "ANALYTICS_MODEL_MANIFEST_PATH": str(settings.manifest_path),
        "ANALYTICS_MODEL_SHA256": settings.model_sha256,
        "ANALYTICS_CHILD_OFFERS_ENABLED": "true",
        "ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH": str(settings.child_offers_repository_path),
        "ANALYTICS_CHILD_OFFERS_PMUM_MIN_MINUTES": "120",
        "ANALYTICS_CHILD_OFFERS_PMUM_MAX_MINUTES": "180",
    }.items():
        monkeypatch.setenv(key, value)
    assert Settings.from_env().child_offer_policy() == V2
