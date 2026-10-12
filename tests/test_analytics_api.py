"""Pruebas de contrato y transporte con fixtures artificiales, nunca modelo real."""

import asyncio
import hashlib
import json
import math
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import joblib
from fastapi.testclient import TestClient

from analytics_service.activities import ACTIVITY_IDS, CATALOG_VERSION, select_activities
from analytics_service.http import TransportGuard, create_app
from analytics_service.pmum import CachedPmum, ModelUnavailable
from analytics_service.settings import Settings
from experiments.hu_pmum_candidate_v1 import EXPECTED_SHA256, FEATURES, MODEL_VERSION
from experiments.hu_pmum_parent_adapter_v2 import estimate, estimate_with_predictor

TOKEN = "test-only-token-0123456789"
HEADERS = {"Authorization": "Bearer " + TOKEN}
VALID = {"age": 9, "sex_code": 1, "weekday_category": 2, "weekend_category": 3,
         "respondent": "parent_or_caregiver", "reference_days": 30}
SELECT = {"request_id": "request-test-01", "context": "voluntary",
          "eligibility_state": "known", "eligibility": {}}


class FixturePredictor:
    """Valor de referencia fabricado para probar el wrapper; no está entrenado."""
    def __init__(self):
        self.value, self.fail = 2.6959, False

    def predict(self, row):
        if self.fail:
            raise RuntimeError("fixture error")
        return [self.value]


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.model, self.manifest = self.root / "model.joblib", self.root / "manifest.json"
        self.artifact = {
            "model": FixturePredictor(), "version": MODEL_VERSION,
            "features": FEATURES, "source_sha256": EXPECTED_SHA256,
            "trained_rows": 803, "sex_codes": [1, 2], "target": "PMUMTotal/9",
        }
        self.metadata = {"model_version": MODEL_VERSION, "features": list(FEATURES),
                         "source_sha256": EXPECTED_SHA256, "n_trained": 803}
        self.write_fixture()
        self.base = Settings(token=TOKEN)

    def tearDown(self):
        self.temp.cleanup()

    def write_fixture(self):
        joblib.dump(self.artifact, self.model)
        self.manifest.write_text(json.dumps(self.metadata), encoding="utf-8")

    def model_settings(self):
        return Settings(token=TOKEN, pmum_enabled=True, model_path=self.model,
                        manifest_path=self.manifest,
                        model_sha256=hashlib.sha256(self.model.read_bytes()).hexdigest())

    def test_default_readiness_reports_historical_disabled(self):
        with TestClient(create_app(self.base)) as c:
            r = c.get("/health")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["capabilities"]["pmum"]["state"], "DISABLED")
            historical = r.json()["capabilities"]["historical"]
            self.assertEqual(historical["state"], "DISABLED")
            self.assertTrue(historical["implemented"])
            self.assertIsNone(historical["configuration_id"])
            self.assertEqual(r.headers["cache-control"], "no-store")

    def test_no_capabilities_is_not_ready_but_alive(self):
        with TestClient(create_app(replace(self.base, activities_enabled=False))) as c:
            self.assertEqual(c.get("/health").status_code, 503)
            self.assertEqual(c.get("/health/live").status_code, 200)

    def test_authentication_required_before_body(self):
        with TestClient(create_app(self.base)) as c:
            for headers in ({}, {"Authorization": "Bearer wrong-token"}):
                with self.subTest(headers=bool(headers)):
                    r = c.post("/v1/activities/select", content="x" * 20000, headers=headers)
                    self.assertEqual(r.status_code, 401)

    def test_unknown_route_and_wrong_method(self):
        with TestClient(create_app(self.base)) as c:
            self.assertEqual(c.get("/missing", headers=HEADERS).status_code, 404)
            self.assertEqual(c.get("/v1/activities/select", headers=HEADERS).status_code, 405)

    def test_historical_and_disabled_pmum_do_not_claim_results(self):
        with TestClient(create_app(self.base)) as c:
            for route in ("/v1/historical/evaluate", "/experimental/pmum-estimate"):
                with self.subTest(route=route):
                    self.assertEqual(c.post(route, json=VALID, headers=HEADERS).status_code, 503)

    def test_content_type_and_body_limit(self):
        with TestClient(create_app(self.base)) as c:
            self.assertEqual(c.post("/v1/activities/select", content="{}", headers=HEADERS).status_code, 415)
            self.assertEqual(c.post("/v1/activities/select", content="x" * 16385,
                                   headers={**HEADERS, "Content-Type": "application/json"}).status_code, 413)

    def test_invalid_json_nonfinite_and_duplicate_keys(self):
        with TestClient(create_app(self.base)) as c:
            for body in ('{', '{"x":NaN}', '{"x":Infinity}', '{"x":1e309}', '{"x":1,"x":2}', b'\xff'):
                with self.subTest(body=repr(body)):
                    self.assertEqual(c.post("/v1/activities/select", content=body,
                        headers={**HEADERS, "Content-Type": "application/json"}).status_code, 400)

    def test_selection_is_repeatable_without_offer_side_effects(self):
        with TestClient(create_app(self.base)) as c:
            with patch("builtins.open", side_effect=AssertionError("La selección no debe abrir archivos")):
                a = c.post("/v1/activities/select", json=SELECT, headers=HEADERS)
                b = c.post("/v1/activities/select", json=SELECT, headers=HEADERS)
            self.assertEqual(a.status_code, 200)
            self.assertEqual(a.json(), b.json())
            self.assertEqual(len(a.json()["activities"]), 3)
            self.assertNotIn("offer_id", a.json())
            self.assertEqual(a.json()["catalog_version"], CATALOG_VERSION)

    def test_selection_fingerprint_changes_with_input(self):
        a = select_activities(SELECT)
        b = select_activities({**SELECT, "context": "bedtime"})
        self.assertNotEqual(a["selection_fingerprint"], b["selection_fingerprint"])

    def test_set_like_inputs_are_canonicalized(self):
        a = select_activities({**SELECT, "interests": ["drawing", "sports"]})
        b = select_activities({**SELECT, "interests": ["sports", "drawing", "drawing"]})
        self.assertEqual(a, b)

    def test_empty_candidates_have_explicit_status(self):
        p = {**SELECT, "eligibility": {"excluded_activity_ids": sorted(ACTIVITY_IDS)}}
        r = select_activities(p)
        self.assertEqual(r["status"], "no_eligible_activities")
        self.assertEqual(r["activities"], [])

    def test_unknown_eligibility_is_distinct_from_none(self):
        p = {"request_id": "req-unknown", "context": "voluntary", "eligibility_state": "unknown"}
        with TestClient(create_app(self.base)) as c:
            r = c.post("/v1/activities/select", json=p, headers=HEADERS)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["reason"], "eligibility_unknown")
            self.assertEqual(r.json()["activities"], [])
            self.assertEqual(c.post("/v1/activities/select", json=SELECT, headers=HEADERS).json()["status"], "selected")

    def test_invalid_selection_does_not_ignore_restrictions(self):
        bad = [
            {"request_id": "r", "context": "voluntary"},
            {**SELECT, "pmum_score": 4},
            {**SELECT, "conditions": ["visual"]},
            {**SELECT, "context": []},
            {**SELECT, "interests": "drawing"},
            {**SELECT, "eligibility": {"unknown_flag": True}},
            {**SELECT, "eligibility": {"allow_requires_other_person": "false"}},
            {**SELECT, "eligibility": {"excluded_activity_ids": ["unknown-id"]}},
            {**SELECT, "eligibility_state": "unknown"},
        ]
        with TestClient(create_app(self.base)) as c:
            for p in bad:
                with self.subTest(payload=p):
                    self.assertEqual(c.post("/v1/activities/select", json=p, headers=HEADERS).status_code, 400)

    def test_bedtime_eligibility_preserves_existing_filters(self):
        r = select_activities({**SELECT, "context": "bedtime", "eligibility": {"allow_requires_other_person": False}})
        self.assertGreater(len(r["activities"]), 0)
        for a in r["activities"]:
            self.assertTrue(a["bedtime_suitable"])
            self.assertEqual(a["activity_level"], "calm")
            self.assertFalse(a["requires_other_person"])

    def test_disabled_activities(self):
        with TestClient(create_app(replace(self.base, activities_enabled=False))) as c:
            self.assertEqual(c.post("/v1/activities/select", json=SELECT, headers=HEADERS).status_code, 503)

    def test_model_loaded_once_and_survives_file_removal(self):
        app = create_app(self.model_settings())
        with patch("joblib.load", wraps=joblib.load) as load:
            with TestClient(app) as c:
                self.assertEqual(load.call_count, 1)
                self.model.unlink()
                for _ in range(2):
                    r = c.post("/experimental/pmum-estimate", json=VALID, headers=HEADERS)
                    self.assertEqual(r.status_code, 200)
                    self.assertEqual(r.json()["estimated_pmum_sf_mean"], 2.6959)
                self.assertEqual(c.get("/health").status_code, 200)
                self.assertEqual(load.call_count, 1)

    def test_artifact_hash_checked_before_deserialization(self):
        settings = replace(self.model_settings(), model_sha256="0" * 64)
        with patch("joblib.load") as load:
            with self.assertRaises(ModelUnavailable):
                CachedPmum(settings)
            load.assert_not_called()

    def test_corrupt_artifact_cannot_start_ready(self):
        for value in ([], {}, "text"):
            joblib.dump(value, self.model)
            with self.subTest(value=value), self.assertRaises(ModelUnavailable):
                with TestClient(create_app(self.model_settings())):
                    self.fail("No debería iniciar")
        self.model.write_bytes(b"not a model")
        with self.assertRaises(ModelUnavailable):
            CachedPmum(self.model_settings())

    def test_manifest_mismatch_and_reference_fail_startup(self):
        for key, value in (("n_trained", 802), ("source_sha256", "wrong"), ("features", ["age"])):
            self.write_fixture()
            changed = {**self.metadata, key: value}
            self.manifest.write_text(json.dumps(changed))
            with self.subTest(key=key), self.assertRaises(ModelUnavailable):
                CachedPmum(self.model_settings())
        self.artifact["model"].value = 3
        self.write_fixture()
        with self.assertRaises(ModelUnavailable):
            CachedPmum(self.model_settings())

    def test_abstentions_preserve_legacy_adapter(self):
        cases = [VALID, {}, [], {**VALID, "sex_code": None}, {**VALID, "age": 12.9},
                 {**VALID, "weekend_category": None}, {**VALID, "reference_days": 7},
                 {**VALID, "respondent": "child"}, {**VALID, "age": True}, {**VALID, "extra": 1}]
        loaded = CachedPmum(self.model_settings())
        for p in cases:
            with self.subTest(payload=p):
                self.assertEqual(loaded.estimate(p), estimate(self.model, p))

    def test_inference_failure_returns_503_and_changes_readiness(self):
        app = create_app(self.model_settings())
        with TestClient(app) as c:
            app.state.pmum._model.fail = True
            r = c.post("/experimental/pmum-estimate", json=VALID, headers=HEADERS)
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.json(), {"error": "model_unavailable"})
            self.assertEqual(c.get("/health").status_code, 503)
            self.assertEqual(c.get("/health/live").status_code, 200)
            self.assertEqual(c.post("/v1/activities/select", json=SELECT, headers=HEADERS).status_code, 200)

    def test_nonfinite_prediction_unavailable(self):
        model = CachedPmum(self.model_settings())
        model._model.value = math.nan
        with self.assertRaises(ModelUnavailable):
            model.estimate(VALID)
        self.assertFalse(model.ready)

    def test_configuration_rejects_invalid_values_and_historical_activation(self):
        for kwargs in ({"token": "short"}, {"token": TOKEN, "port": 0},
                       {"token": TOKEN, "body_timeout_seconds": float("nan")},
                       {"token": TOKEN, "pmum_enabled": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Settings(**kwargs)
        with patch.dict(os.environ, {"ANALYTICS_SERVICE_TOKEN": TOKEN, "ANALYTICS_HISTORICAL_ENABLED": "true"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_env()


class GuardTests(unittest.TestCase):
    def run_guard(self, events, headers=None, stall=False):
        messages = []
        settings = Settings(token=TOKEN, body_timeout_seconds=0.02)
        async def dummy(scope, receive, send):
            messages.append({"passed": True, "body": (await receive()).get("body")})
        scope = {"type": "http", "method": "POST", "path": "/v1/activities/select",
                 "headers": [(b"authorization", ("Bearer " + TOKEN).encode())] + (headers or [])}
        async def receive():
            if events:
                return events.pop(0)
            if stall:
                await asyncio.Event().wait()
            return {"type": "http.disconnect"}
        async def send(event):
            messages.append(event)
        asyncio.run(TransportGuard(dummy, settings)(scope, receive, send))
        return messages

    def test_slow_body_times_out(self):
        messages = self.run_guard([{"type": "http.request", "body": b"{", "more_body": True}], stall=True)
        self.assertEqual(messages[0]["status"], 408)

    def test_chunked_body_limit(self):
        messages = self.run_guard([{"type": "http.request", "body": b"x" * 16385}])
        self.assertEqual(messages[0]["status"], 413)

    def test_declared_length_mismatch(self):
        messages = self.run_guard([{"type": "http.request", "body": b"{}"}], [(b"content-length", b"3")])
        self.assertEqual(messages[0]["status"], 400)

    def test_oversized_length_does_not_read(self):
        messages = self.run_guard([], [(b"content-length", b"20000")], stall=True)
        self.assertEqual(messages[0]["status"], 413)

    def test_duplicate_length_and_conflicting_framing_rejected(self):
        for headers in ([(b"content-length", b"2"), (b"content-length", b"2")],
                        [(b"content-length", b"2"), (b"transfer-encoding", b"chunked")],
                        [(b"content-length", b"-1")], [(b"content-length", b"9" * 5000)]):
            with self.subTest(headers=headers):
                self.assertEqual(self.run_guard([], headers)[0]["status"], 400)


if __name__ == "__main__":
    unittest.main()
