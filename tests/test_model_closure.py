"""Regresiones de contraejemplos; artefactos y perfiles exclusivamente ficticios."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from analytics_service.http import create_app
from experiments.hu_pmum_parent_adapter_v2 import estimate_with_predictor

from analytics_service.pmum import CachedPmum, ModelUnavailable
from analytics_service.pmum_manifest import read_manifest, validate_manifest
from analytics_service.historical_api import (
    HistoricalRuntime,
    HistoricalUnavailable,
    parse_representation,
)
from historical.analyzer import analyze_c1_representation
from historical.persistence import deserialize_analyzer_state, serialize_analyzer_state
from historical.receipts import serialize_analysis_result, deserialize_analysis_result
from tests import test_analytics_api as analytics_fixture
from tests import test_historical_api as historical_fixture
from tools.validation.audit_c1_repository import audit_snapshot
from tools.validation.audit_pmum_methodology import audit, index_fingerprint
from tools.validation.verify_pmum_artifact_v1 import verify

ROOT = Path(__file__).resolve().parents[1]
VALID = analytics_fixture.VALID
body = historical_fixture.body


class PmumClosureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = analytics_fixture.AnalyticsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_extreme_integer_age_abstains_without_calling_predictor(self):
        from unittest.mock import Mock

        predictor = Mock(side_effect=AssertionError("Entrada fuera del dominio"))
        for age in (10**400, -(10**400)):
            with self.subTest(positive=age > 0):
                self.assertEqual(
                    estimate_with_predictor({**VALID, "age": age}, predictor),
                    {"status": "unavailable", "reason": "invalid_feature_value"},
                )
        predictor.assert_not_called()

    def test_extreme_integer_age_is_http_abstention_and_preserves_readiness(self):
        with TestClient(create_app(self.fixture.model_settings())) as client:
            for age in (10**400, -(10**400)):
                with self.subTest(positive=age > 0):
                    response = client.post(
                        "/experimental/pmum-estimate",
                        json={**VALID, "age": age},
                        headers=analytics_fixture.HEADERS,
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        response.json(),
                        {"status": "unavailable", "reason": "invalid_feature_value"},
                    )
            self.assertEqual(client.get("/health").status_code, 200)
            valid = client.post(
                "/experimental/pmum-estimate", json=VALID,
                headers=analytics_fixture.HEADERS,
            )
            self.assertEqual(valid.status_code, 200)
            self.assertEqual(valid.json()["estimated_pmum_sf_mean"], 2.6959)

    def test_faithful_manifest_preserves_prediction_and_abstentions(self):
        f = self.fixture
        model = CachedPmum(f.model_settings())
        self.assertEqual(model.estimate(VALID)["estimated_pmum_sf_mean"], 2.6959)
        self.assertEqual(
            model.estimate({**VALID, "weekend_category": None})["reason"],
            "missing_parent_answer",
        )
        self.assertEqual(
            model.estimate({**VALID, "sex_code": None})["status"], "unavailable"
        )

    def test_wrong_manifest_output_scale_is_rejected_before_joblib(self):
        f = self.fixture
        f.metadata["target"] = "PMUM total, 9 to 45"
        f.write_fixture()
        with patch("joblib.load") as load, self.assertRaises(ModelUnavailable):
            CachedPmum(f.model_settings())
        load.assert_not_called()

    def test_manifest_cannot_claim_approved_or_another_source(self):
        f = self.fixture
        for key, value in [
            ("deployment_status", "APPROVED"),
            ("source", "other dataset"),
        ]:
            m = {**f.metadata, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_manifest(m)

    def test_counts_cannot_be_floats_or_booleans(self):
        f = self.fixture
        for key, value in [("n_trained", 803.0), ("sex_code_4_excluded", True)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_manifest({**f.metadata, key: value})
        f.artifact["trained_rows"] = 803.0
        f.write_fixture()
        with self.assertRaises(ModelUnavailable):
            CachedPmum(f.model_settings())
        f.artifact["trained_rows"] = 803
        f.artifact["sex_codes"] = [True, 2]
        f.write_fixture()
        with self.assertRaises(ModelUnavailable):
            CachedPmum(f.model_settings())

    def test_incomplete_manifest_and_naive_timestamp_are_rejected(self):
        f = self.fixture
        m = deepcopy(f.metadata)
        m.pop("target")
        with self.assertRaises(ValueError):
            validate_manifest(m)
        with self.assertRaises(ValueError):
            validate_manifest({**f.metadata, "created_utc": "2026-10-07T18:52:05"})

    def test_duplicate_keys_and_oversized_manifest_are_rejected(self):
        f = self.fixture
        raw = json.dumps(f.metadata)
        f.manifest.write_text(raw[:-1] + ',"n_trained":803}')
        with self.assertRaises(ValueError):
            read_manifest(f.manifest)
        f.manifest.write_bytes(b" " * 65537)
        with self.assertRaises(ValueError):
            read_manifest(f.manifest)

    def test_wrong_prediction_type_or_shape_disables_pmum(self):
        f = self.fixture
        for value in ("2.6959", True, [2.6959]):
            model = CachedPmum(f.model_settings())
            model._model.value = value
            with self.subTest(value=value), self.assertRaises(ModelUnavailable):
                model.estimate(VALID)
            self.assertFalse(model.ready)

    def test_evaluation_tool_rejects_wrong_source_without_fitting(self):
        f = self.fixture
        p = f.root / "source.zip"
        p.write_bytes(b"not the verified dataset")
        with (
            patch("tools.validation.audit_pmum_methodology.make_ridge") as fit,
            self.assertRaises(ValueError),
        ):
            audit(p)
        fit.assert_not_called()
        self.assertEqual(index_fingerprint([1, 2]), index_fingerprint([1, 2]))
        self.assertNotEqual(index_fingerprint([1, 2]), index_fingerprint([2, 1]))

    def test_original_artifact_tool_rejects_fixture_before_deserializing(self):
        f = self.fixture
        from experiments.hu_pmum_candidate_v1 import MODEL_VERSION

        (f.root / (MODEL_VERSION + ".joblib")).write_bytes(f.model.read_bytes())
        (f.root / (MODEL_VERSION + ".json")).write_bytes(f.manifest.read_bytes())
        with patch("tools.validation.verify_pmum_artifact_v1.CachedPmum") as loader:
            with self.assertRaises(ValueError):
                verify(f.root)
        loader.assert_not_called()


class C1ClosureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = historical_fixture.HistoricalApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with self.fixture.client() as c:
            self.original_results = self.fixture.seed(c)

    def document(self):
        return json.loads(self.fixture.repository.read_bytes())

    def store(self, document):
        self.fixture.repository.write_text(json.dumps(document), encoding="utf-8")

    def reject_startup_without_rewriting(self, document):
        self.store(document)
        before = self.fixture.repository.read_bytes()
        with self.assertRaises(HistoricalUnavailable):
            HistoricalRuntime(self.fixture.settings)
        self.assertEqual(self.fixture.repository.read_bytes(), before)

    def test_receipt_observed_value_must_match_record(self):
        d = self.document()
        r = body(3)["representation"]["representation_record_id"]
        d["receipts"][r]["result"]["evaluation"]["observed_value"] = 999
        self.reject_startup_without_rewriting(d)

    def test_outcome_must_match_stored_threshold_and_state(self):
        d = self.document()
        r = body(3)["representation"]["representation_record_id"]
        d["receipts"][r]["result"]["evaluation"]["outcome"] = "CHANGE"
        self.reject_startup_without_rewriting(d)

    def test_emission_must_match_crossing_and_evaluation(self):
        d = self.document()
        r = body(4)["representation"]["representation_record_id"]
        d["receipts"][r]["result"]["emission"] = {"decision": "NO_EMIT", "event": None}
        self.reject_startup_without_rewriting(d)

    def test_history_count_must_match_prior_usable_records(self):
        d = self.document()
        r = body(3)["representation"]["representation_record_id"]
        d["receipts"][r]["result"]["reference"]["history_count"] = 0
        d["receipts"][r]["result"]["evaluation"]["reference_history_count"] = 0
        self.reject_startup_without_rewriting(d)

    def test_boolean_numbers_cannot_pass_as_zero_or_configuration_schema(self):
        original = self.document()
        for field in ("positive_cusum", "schema_version"):
            d = deepcopy(original)
            if field == "schema_version":
                d["analytics_binding"]["configuration"][field] = True
            else:
                d["receipts"][body(3)["representation"]["representation_record_id"]][
                    "result"
                ]["evaluation"][field] = False
            self.reject_startup_without_rewriting(d)

    def test_snapshot_audit_preserves_receipts_and_runtime_replays_original(self):
        f = self.fixture
        before = f.repository.read_bytes()
        report = audit_snapshot(f.repository, f.profile)
        self.assertEqual(report["records"], 5)
        self.assertFalse(report["original_receipts_rewritten"])
        self.assertEqual(sha256(before).hexdigest(), report["repository_sha256"])
        with f.client() as c:
            for day, original in enumerate(self.original_results):
                value = [90, 100, 110, 100, 400][day]
                replay = f.post(c, body(day, value)).json()
                self.assertTrue(replay["replayed"])
                self.assertEqual(replay["result"], original["result"])
        self.assertEqual(f.repository.read_bytes(), before)

    def test_full_audit_detects_coherent_reference_from_wrong_history(self):
        f = self.fixture
        d = self.document()
        r = body(4)["representation"]["representation_record_id"]
        receipt = d["receipts"][r]
        saved = deserialize_analysis_result(receipt["result"])
        profile = HistoricalRuntime(f.settings)
        try:
            wrong_history = [
                parse_representation(body(day, value)["representation"])
                for day, value in enumerate([80, 90, 100, 90])
            ]
            forged = analyze_c1_representation(
                parse_representation(body(4, 400)["representation"]),
                wrong_history,
                deserialize_analyzer_state(receipt["previous_state"]),
                profile.profile.config,
                evaluation_id=saved.evaluation.evaluation_id,
                event_id=saved.emission.event.event_id,
                analysis_version=profile.profile.analysis_version,
                emitter_version=profile.profile.emitter_version,
                computed_at=saved.evaluation.computed_at,
                emitted_at=saved.emission.event.emitted_at,
            )
            receipt["result"] = serialize_analysis_result(forged)
            for sid, state in d["streams"].items():
                state["state"] = serialize_analyzer_state(forged.next_state)
        finally:
            profile.close()
        self.store(d)
        before = f.repository.read_bytes()
        # Calcular sobre una referencia conservada no equivale a reconstruirla.
        runtime = HistoricalRuntime(f.settings)
        self.assertTrue(runtime.check_ready())
        runtime.close()
        with self.assertRaises(ValueError):
            audit_snapshot(f.repository, f.profile)
        self.assertEqual(f.repository.read_bytes(), before)

    def test_missing_does_not_advance_state_and_zero_builds_history(self):
        f = self.fixture
        with f.client() as c:
            missing = f.post(c, body(5, None, status="MISSING")).json()
            self.assertEqual(missing["result"]["evaluation"]["outcome"], "ABSTAIN")
            self.assertEqual(
                missing["result"]["next_state"],
                self.original_results[-1]["result"]["next_state"],
            )
            zero = f.post(c, body(6, 0, status="OBSERVED_ZERO")).json()
            self.assertEqual(zero["result"]["reference"]["history_count"], 5)
        self.assertEqual(audit_snapshot(f.repository, f.profile)["records"], 7)

    def test_audit_cli_never_overwrites_an_existing_output(self):
        f = self.fixture
        out = f.directory / "report.json"
        out.write_text("KEEP")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/validation/audit_c1_repository.py"),
                "--repository",
                str(f.repository),
                "--config",
                str(f.profile),
                "--output",
                str(out),
            ],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(out.read_text(), "KEEP")
