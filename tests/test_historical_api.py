"""Integración del núcleo publicado, persistencia real y transporte HTTP.

Todos los perfiles numéricos son fixtures, nunca umbrales de producto.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from analytics_service.historical_api import HistoricalRuntime, HistoricalUnavailable
from analytics_service.historical_config import HistoricalProfile
from analytics_service.http import create_app
from analytics_service.settings import Settings
from historical.analyzer import analyze_c1_representation
from historical.persistence import FileHistoricalRepository, HistoricalStreamKey
from historical.receipts import serialize_analysis_result

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "tests/fixtures/historical_c1_smoke_only.json").read_text())
TOKEN = "historical-test-only-20261011"
HEADERS = {"Authorization": "Bearer " + TOKEN}
UTC = timezone.utc


def body(day=0, value=90, subject="device-test-01", status="OBSERVED"):
    start = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=day)
    return {
        "request_id": "req-" + subject + "-" + str(day),
        "representation": {
            "representation_record_id": "rep-" + subject + "-" + str(day),
            "representation_spec_id": "daily_use_duration_minutes_v2", "subject_id": subject,
            "phenomenon": "DAILY_USE_DURATION", "interval_start": start.isoformat(),
            "interval_end": (start + timedelta(days=1)).isoformat(), "value": value,
            "unit": "minutes", "status": status, "coverage": {"value": None, "basis": None},
            "quality_flags": [], "provenance": {
                "source_id": "synthetic-http-fixture", "source_version": "test-v1",
                "source_semantics": "fictitious canonical representation",
                "adapter_version": "v2", "input_fingerprint": "fixture-" + str(day),
            }, "computed_at": (start + timedelta(days=1)).isoformat(),
        },
    }


class HistoricalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.profile = self.directory / "profile.json"
        self.profile.write_text(json.dumps(PROFILE), encoding="utf-8")
        self.repository = self.directory / "state" / "history.json"
        self.settings = Settings(token=TOKEN, historical_enabled=True,
                                 historical_config_path=self.profile,
                                 historical_repository_path=self.repository)
        self.addCleanup(self.temp.cleanup)

    def client(self, settings=None):
        return TestClient(create_app(settings or self.settings))

    def post(self, client, payload=None):
        return client.post("/v1/historical/evaluate", json=payload or body(), headers=HEADERS)

    def seed(self, client):
        results = []
        for day, value in enumerate([90, 100, 110, 100, 400]):
            response = self.post(client, body(day, value))
            self.assertEqual(response.status_code, 200, response.text)
            results.append(response.json())
        return results

    def test_cold_start_is_persisted_abstention_with_server_ids(self):
        with self.client() as client:
            response = self.post(client)
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            evaluation = result["result"]["evaluation"]
            self.assertEqual(evaluation["outcome"], "ABSTAIN")
            self.assertEqual(evaluation["abstention_reason"], "INSUFFICIENT_HISTORY")
            self.assertTrue(evaluation["evaluation_id"].startswith("eval-"))
            self.assertFalse(result["replayed"])
            document = json.loads(self.repository.read_text())
            self.assertEqual(len(document["representations"]), 1)
            self.assertEqual(len(document["receipts"]), 1)
            self.assertEqual(document["analytics_binding"]["configuration"], PROFILE)
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_health_reports_enabled_profile_without_paths_or_subjects(self):
        with self.client() as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            historical = response.json()["capabilities"]["historical"]
            self.assertEqual(historical["state"], "READY")
            self.assertTrue(historical["implemented"])
            self.assertEqual(historical["configuration_id"], PROFILE["configuration_id"])
            self.assertNotIn(str(self.directory), response.text)
            self.assertFalse(self.repository.exists())

    def test_only_historical_can_make_service_ready(self):
        with self.client(replace(self.settings, activities_enabled=False)) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(self.post(client).status_code, 200)

    def test_configuration_is_required_and_strict(self):
        for field in PROFILE:
            changed = deepcopy(PROFILE)
            changed.pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                HistoricalProfile.from_payload(changed)
        for key, value in (("k", None), ("k", True), ("k", -1), ("threshold", 0),
                           ("min_history", 0), ("min_history", 3.0), ("min_history", True)):
            changed = deepcopy(PROFILE)
            changed["detector"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                HistoricalProfile.from_payload(changed)
        for key, value in (("reference_policy", "rolling"), ("scope", "production"),
                           ("representation_spec_id", "interactive_screen_device_minutes_v3_draft"),
                           ("extra", 1), ("schema_version", True)):
            changed = {**PROFILE, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                HistoricalProfile.from_payload(changed)

    def test_missing_or_invalid_profile_prevents_startup(self):
        for content in ("{}", "[]", '{"k":NaN}', '{"k":1,"k":2}'):
            self.profile.write_text(content)
            with self.subTest(content=content), self.assertRaises(HistoricalUnavailable):
                with self.client():
                    self.fail("No debe iniciar")
        self.profile.unlink()
        with self.assertRaises(HistoricalUnavailable):
            with self.client():
                self.fail("No debe iniciar")

    def test_paths_must_be_explicit_and_absolute(self):
        for changes in ({"historical_config_path": None}, {"historical_repository_path": None},
                        {"historical_repository_path": Path("relative.json")},
                        {"historical_enabled": "true"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.settings, **changes)

    def test_configuration_cannot_overlap_repository_or_temporary_files(self):
        for filename in ("profile.json", ".profile.json.tmp", "profile.json.writer.lock"):
            target = self.directory / filename
            config = self.directory / "profile.json"
            if filename != "profile.json":
                config = target
                config.write_text(json.dumps(PROFILE))
                target = self.directory / "profile.json"
            with self.subTest(filename=filename), self.assertRaises(HistoricalUnavailable):
                HistoricalRuntime(replace(self.settings, historical_config_path=config,
                                          historical_repository_path=target))

    def test_transport_auth_content_type_invalid_json_and_limits(self):
        with self.client() as client:
            self.assertEqual(client.post("/v1/historical/evaluate", json=body()).status_code, 401)
            self.assertEqual(client.post("/v1/historical/evaluate", content="{}", headers=HEADERS).status_code, 415)
            for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":1e309}', '[]'):
                r = client.post("/v1/historical/evaluate", content=raw,
                                headers={**HEADERS, "Content-Type": "application/json"})
                self.assertEqual(r.status_code, 400)
            r = client.post("/v1/historical/evaluate", content="x" * 16385, headers=HEADERS)
            self.assertEqual(r.status_code, 413)
            self.assertFalse(self.repository.exists())

    def test_unknown_fields_and_no_parameter_override(self):
        with self.client() as client:
            cases = [{}, [], {**body(), "detector": {"k": 0}}, {**body(), "event_id": "caller-id"}]
            for field in ("age", "pmum_score", "next_state", "configuration_id"):
                p = body()
                p["representation"][field] = 1
                cases.append(p)
            for p in cases:
                with self.subTest(payload=p):
                    r = client.post("/v1/historical/evaluate", json=p, headers=HEADERS)
                    self.assertEqual(r.status_code, 400)
            self.assertFalse(self.repository.exists())

    def test_representation_status_zero_and_missing_are_not_conflated(self):
        with self.client() as client:
            for subject, value, status in (("zero", 0, "OBSERVED_ZERO"),
                                           ("missing", None, "MISSING"),
                                           ("not-applicable", None, "NOT_APPLICABLE")):
                r = self.post(client, body(value=value, subject=subject, status=status))
                self.assertEqual(r.status_code, 200, r.text)
                if value is None:
                    self.assertIsNone(r.json()["result"]["evaluation"]["observed_value"])
            rows = json.loads(self.repository.read_text())["representations"]
            self.assertEqual([r["status"] for r in rows], ["OBSERVED_ZERO", "MISSING", "NOT_APPLICABLE"])

    def test_invalid_representation_is_rejected_before_persistence(self):
        changes = [
            ("value", -1), ("value", True), ("value", "90"), ("value", []),
            ("value", 0), ("status", "invented"), ("interval_start", "2026-09-01T00:00:00"),
            ("interval_end", "2026-08-31T00:00:00Z"), ("subject_id", ""),
            ("unit", "hours"), ("phenomenon", "PMUM"),
            ("representation_spec_id", "interactive_screen_device_minutes_v3_draft"),
            ("coverage", {"value": True, "basis": None}), ("quality_flags", "bad"),
        ]
        with self.client() as client:
            for field, value in changes:
                p = body()
                p["representation"][field] = value
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.post(client, p).status_code, 400)
            for status in ("MISSING", "NOT_APPLICABLE"):
                self.assertEqual(self.post(client, body(value=1, status=status)).status_code, 400)
            self.assertFalse(self.repository.exists())

    def test_direct_published_core_and_api_produce_same_result(self):
        with self.client() as client:
            responses = self.seed(client)
            runtime = client.app.state.historical
            history = []
            from analytics_service.historical_api import parse_representation
            from historical.analyzer import HistoricalAnalyzerState
            state = HistoricalAnalyzerState()
            for day, value in enumerate([90, 100, 110, 100, 400]):
                current = parse_representation(body(day, value)["representation"])
                actual = responses[day]["result"]
                evaluation = actual["evaluation"]
                event = actual["emission"]["event"]
                expected = analyze_c1_representation(
                    current=current, history=history, previous_state=state, config=runtime.profile.config,
                    evaluation_id=evaluation["evaluation_id"],
                    event_id=event["event_id"] if event else "unused-id",
                    analysis_version=runtime.profile.analysis_version,
                    emitter_version=runtime.profile.emitter_version,
                    computed_at=datetime.fromisoformat(evaluation["computed_at"]),
                    emitted_at=datetime.fromisoformat(event["emitted_at"]) if event else datetime.now(UTC),
                )
                self.assertEqual(actual, serialize_analysis_result(expected))
                history.append(current)
                state = expected.next_state
            self.assertEqual(responses[3]["result"]["evaluation"]["outcome"], "NO_CHANGE")
            self.assertEqual(responses[4]["result"]["emission"]["decision"], "EMIT")

    def test_retry_preserves_original_result_and_bytes(self):
        with self.client() as client:
            results = self.seed(client)
            before = self.repository.read_bytes()
            retry = body(4, 400)
            retry["request_id"] = "another-http-attempt"
            retry["representation"]["computed_at"] = "2026-10-11T20:00:00Z"
            with patch("historical.service.analyze_c1_representation", side_effect=AssertionError("No recalcular")):
                r = self.post(client, retry)
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()["replayed"])
            self.assertEqual(r.json()["result"], results[4]["result"])
            self.assertEqual(self.repository.read_bytes(), before)

    def test_compatible_timezone_encodings_are_normalized(self):
        with self.client() as client:
            first = self.post(client).json()
            retry = body()
            retry["representation"]["interval_start"] = "2026-08-31T21:00:00-03:00"
            retry["representation"]["interval_end"] = "2026-09-01T21:00:00-03:00"
            repeated = self.post(client, retry)
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(repeated.json()["result"], first["result"])

    def test_conflicting_retry_is_409_without_health_failure_or_write(self):
        with self.client() as client:
            self.post(client)
            before = self.repository.read_bytes()
            for field, value in (("value", 91), ("subject_id", "another-subject"),
                                 ("quality_flags", ["changed"])):
                retry = body()
                retry["representation"][field] = value
                r = self.post(client, retry)
                self.assertEqual(r.status_code, 409)
                self.assertEqual(r.json()["error"], "representation_conflict")
            self.assertEqual(self.repository.read_bytes(), before)
            self.assertEqual(client.get("/health").status_code, 200)

    def test_out_of_order_and_overlap_are_409_without_changes(self):
        with self.client() as client:
            self.post(client, body(2, 110))
            before = self.repository.read_bytes()
            for p in (body(1, 100), body(2, 110)):
                p["representation"]["representation_record_id"] += "-different"
                r = self.post(client, p)
                self.assertEqual(r.status_code, 409)
                self.assertEqual(r.json()["error"], "historical_order_conflict")
            self.assertEqual(self.repository.read_bytes(), before)

    def test_gap_is_allowed_and_subjects_do_not_share_reference(self):
        with self.client() as client:
            self.seed(client)
            gap = self.post(client, body(10, 120))
            self.assertEqual(gap.status_code, 200)
            other = self.post(client, body(10, 120, subject="device-test-02"))
            self.assertEqual(other.status_code, 200)
            self.assertEqual(other.json()["result"]["reference"]["history_count"], 0)

    def test_missing_keeps_previous_cusum_and_last_eligible_statistic(self):
        with self.client() as client:
            results = self.seed(client)
            r = self.post(client, body(5, None, status="MISSING"))
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["result"]["next_state"], results[-1]["result"]["next_state"])
            self.assertEqual(r.json()["result"]["evaluation"]["abstention_reason"], "CURRENT_MISSING")

    def test_restart_recovers_original_event_and_no_change_and_abstention(self):
        with self.client() as client:
            first = self.seed(client)
        before = self.repository.read_bytes()
        with self.client() as client:
            for day, value in enumerate([90, 100, 110, 100, 400]):
                r = self.post(client, body(day, value))
                self.assertEqual(r.status_code, 200, r.text)
                self.assertTrue(r.json()["replayed"])
                self.assertEqual(r.json()["result"], first[day]["result"])
        self.assertEqual(self.repository.read_bytes(), before)

    def test_same_record_concurrent_requests_commit_once(self):
        with self.client() as client:
            with ThreadPoolExecutor(max_workers=8) as pool:
                responses = list(pool.map(lambda _: self.post(client), range(16)))
            self.assertEqual([r.status_code for r in responses], [200] * 16)
            results = [r.json() for r in responses]
            self.assertEqual(sum(not r["replayed"] for r in results), 1)
            self.assertTrue(all(r["result"] == results[0]["result"] for r in results))
            self.assertEqual(len(json.loads(self.repository.read_text())["representations"]), 1)

    def test_concurrent_subjects_do_not_lose_records(self):
        with self.client() as client:
            with ThreadPoolExecutor(max_workers=8) as pool:
                responses = list(pool.map(lambda i: self.post(client, body(subject="device-" + str(i))), range(16)))
            self.assertEqual([r.status_code for r in responses], [200] * 16)
            document = json.loads(self.repository.read_text())
            self.assertEqual(len(document["representations"]), 16)
            self.assertEqual(len(document["streams"]), 16)
            self.assertEqual(len(document["receipts"]), 16)

    def test_second_writer_in_same_process_cannot_start_then_lock_releases(self):
        with self.client():
            with self.assertRaises(HistoricalUnavailable):
                HistoricalRuntime(self.settings)
        runtime = HistoricalRuntime(self.settings)
        runtime.close()

    def test_second_writer_process_is_rejected(self):
        script = """
import sys
from pathlib import Path
from analytics_service.settings import Settings
from analytics_service.historical_api import HistoricalRuntime, HistoricalUnavailable
try:
    runtime=HistoricalRuntime(Settings(token='child-test-token-20261011', historical_enabled=True,
        historical_config_path=Path(sys.argv[1]), historical_repository_path=Path(sys.argv[2])))
except HistoricalUnavailable:
    print('EXCLUSIVE_WRITER_REJECTED');sys.exit(7)
runtime.close();sys.exit(0)
"""
        with self.client():
            result = subprocess.run([sys.executable, "-c", script, str(self.profile), str(self.repository)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(result.stdout.strip(), "EXCLUSIVE_WRITER_REJECTED")

    def test_changed_profile_cannot_reuse_existing_repository(self):
        with self.client() as client:
            self.seed(client)
        before = self.repository.read_bytes()
        for field, value in (("configuration_id", "different"), ("analysis_version", "different"),
                             ("emitter_version", "different")):
            self.profile.write_text(json.dumps({**PROFILE, field: value}))
            with self.subTest(field=field), self.assertRaises(HistoricalUnavailable):
                with self.client():
                    self.fail("No debe iniciar")
        changed = deepcopy(PROFILE)
        changed["detector"]["threshold"] = 4
        self.profile.write_text(json.dumps(changed))
        with self.assertRaises(HistoricalUnavailable):
            with self.client():
                self.fail("No debe iniciar")
        self.assertEqual(self.repository.read_bytes(), before)

    def test_profile_is_loaded_once_and_not_hot_reloaded(self):
        with self.client() as client:
            first = client.get("/health").json()["capabilities"]["historical"]
            self.profile.write_text("{}")
            self.assertEqual(self.post(client).status_code, 200)
            self.assertEqual(client.get("/health").json()["capabilities"]["historical"], first)

    def test_legacy_or_unbound_repository_is_not_silently_imported(self):
        self.repository.parent.mkdir()
        self.repository.write_text(json.dumps(FileHistoricalRepository(self.repository)._empty_document()))
        before = self.repository.read_bytes()
        with self.assertRaises(HistoricalUnavailable):
            with self.client():
                self.fail("No debe iniciar")
        self.assertEqual(self.repository.read_bytes(), before)

    def test_corrupt_file_and_receipt_chain_prevent_restart(self):
        with self.client() as client:
            self.seed(client)
        original = self.repository.read_bytes()
        document = json.loads(original)
        sid = next(iter(document["streams"]))
        first_id = document["representations"][0]["representation_record_id"]
        last_id = document["representations"][-1]["representation_record_id"]
        cases = [b"broken", b'{"a":1,"a":2}']
        for change in ("receipt_missing", "state_changed", "previous_state_changed", "duplicate_record"):
            d = deepcopy(document)
            if change == "receipt_missing":
                d["receipts"].pop(first_id)
            elif change == "state_changed":
                d["streams"][sid]["state"]["positive_cusum"] = 999
            elif change == "previous_state_changed":
                d["receipts"][last_id]["previous_state"]["positive_cusum"] = 999
            else:
                d["representations"].append(d["representations"][0])
            cases.append(json.dumps(d).encode())
        for data in cases:
            self.repository.write_bytes(data)
            with self.subTest(data=data[:60]), self.assertRaises(HistoricalUnavailable):
                with self.client():
                    self.fail("No debe iniciar")
            self.assertEqual(self.repository.read_bytes(), data)

    def test_storage_failure_marks_unavailable_but_other_capacity_survives(self):
        with self.client() as client:
            with patch.object(client.app.state.historical.repository, "save_analysis_progress", side_effect=OSError("disk error")):
                r = self.post(client)
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.json(), {"error": "historical_unavailable"})
            self.assertNotIn(str(self.repository), r.text)
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(client.get("/health/live").status_code, 200)
            p = {"request_id": "still-available", "context": "voluntary", "eligibility_state": "unknown"}
            self.assertEqual(client.post("/v1/activities/select", json=p, headers=HEADERS).status_code, 200)
            self.assertEqual(self.post(client).status_code, 503)

    def test_failure_before_replace_keeps_previous_committed_file(self):
        with self.client() as client:
            self.post(client)
            before = self.repository.read_bytes()
            with patch("historical.persistence.os.replace", side_effect=OSError("rename failed")):
                response = self.post(client, body(1, 100))
            self.assertEqual(response.status_code, 503)
            self.assertEqual(self.repository.read_bytes(), before)
            self.assertFalse(self.repository.with_name("." + self.repository.name + ".tmp").exists())
        with self.client() as client:
            self.assertEqual(self.post(client, body(1, 100)).status_code, 200)

    def test_response_lost_after_commit_recovers_original_on_restart(self):
        with self.client() as client:
            runtime = client.app.state.historical
            original_save = runtime.repository.save_analysis_progress
            def save_then_fail(**kwargs):
                original_save(**kwargs)
                raise OSError("response lost after commit")
            with patch.object(runtime.repository, "save_analysis_progress", side_effect=save_then_fail):
                self.assertEqual(self.post(client).status_code, 503)
        document = json.loads(self.repository.read_text())
        expected = next(iter(document["receipts"].values()))["result"]
        with self.client() as client:
            with patch("historical.service.analyze_c1_representation", side_effect=AssertionError("No recalcular")):
                response = self.post(client)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["replayed"])
            self.assertEqual(response.json()["result"], expected)

    def test_runtime_detects_repository_corruption_before_new_processing(self):
        with self.client() as client:
            self.post(client)
            self.repository.write_text("{}")
            response = self.post(client, body(1, 100))
            self.assertEqual(response.status_code, 503)
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(self.repository.read_text(), "{}")

    def test_health_detects_corruption_without_an_evaluation_request(self):
        with self.client() as client:
            self.post(client)
            self.repository.write_text("{}")
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(client.get("/health/live").status_code, 200)
            self.assertEqual(self.repository.read_text(), "{}")

    def test_disappeared_repository_is_not_recreated_live_or_after_restart(self):
        with self.client() as client:
            self.post(client)
            marker = self.repository.with_name(self.repository.name + ".initialized")
            self.assertTrue(marker.exists())
            self.repository.unlink()
            self.assertEqual(self.post(client, body(1, 100)).status_code, 503)
            self.assertFalse(self.repository.exists())
        with self.assertRaises(HistoricalUnavailable):
            with self.client():
                self.fail("No debe inventar historial vacio")
        self.assertFalse(self.repository.exists())

    @unittest.skipUnless(os.name == "posix", "Windows requiere comprobar su reserva nativa; no borra un archivo bloqueado")
    def test_lost_writer_lease_path_marks_unavailable(self):
        with self.client() as client:
            lease = self.repository.with_name(self.repository.name + ".writer.lock")
            lease.unlink()
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(self.post(client).status_code, 503)
            self.assertFalse(self.repository.exists())

    def test_all_three_capacities_coexist_and_pmum_failure_does_not_change_historical(self):
        import joblib
        from tests.test_analytics_api import FixturePredictor, FEATURES, EXPECTED_SHA256, MODEL_VERSION, VALID
        model = self.directory / "fixture.joblib"
        manifest = self.directory / "fixture.json"
        joblib.dump({"model": FixturePredictor(), "version": MODEL_VERSION, "features": FEATURES,
                     "source_sha256": EXPECTED_SHA256, "trained_rows": 803,
                     "sex_codes": [1, 2], "target": "PMUMTotal/9"}, model)
        manifest.write_text(json.dumps({"model_version": MODEL_VERSION, "features": FEATURES,
                                        "source_sha256": EXPECTED_SHA256, "n_trained": 803}))
        settings = replace(self.settings, pmum_enabled=True, model_path=model, manifest_path=manifest,
                           model_sha256=hashlib.sha256(model.read_bytes()).hexdigest())
        with self.client(settings) as client:
            health = client.get("/health").json()
            self.assertEqual([v["state"] for v in health["capabilities"].values()], ["READY"] * 3)
            self.assertEqual(client.post("/experimental/pmum-estimate", json=VALID, headers=HEADERS).status_code, 200)
            first = self.post(client).json()
            client.app.state.pmum._model.fail = True
            self.assertEqual(client.post("/experimental/pmum-estimate", json=VALID, headers=HEADERS).status_code, 503)
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(self.post(client).json()["result"], first["result"])
            self.assertEqual(client.get("/health").json()["capabilities"]["historical"]["state"], "READY")

    def test_concurrent_conflicting_payloads_commit_exactly_one(self):
        with self.client() as client:
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda v: self.post(client, body(value=v)), [90, 91]))
            self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
            rows = json.loads(self.repository.read_text())["representations"]
            self.assertEqual(len(rows), 1)
            self.assertIn(rows[0]["value"], [90, 91])

    def test_process_termination_releases_exclusive_writer(self):
        script = """
import sys
from pathlib import Path
from analytics_service.settings import Settings
from analytics_service.historical_api import HistoricalRuntime
runtime=HistoricalRuntime(Settings(token='child-test-token-20261011', historical_enabled=True,
    historical_config_path=Path(sys.argv[1]), historical_repository_path=Path(sys.argv[2])))
print('READY', flush=True)
sys.stdin.read()
runtime.close()
"""
        child = subprocess.Popen([sys.executable, "-c", script, str(self.profile), str(self.repository)],
                                 cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertEqual(pool.submit(child.stdout.readline).result(timeout=10).strip(), "READY")
            with self.assertRaises(HistoricalUnavailable):
                HistoricalRuntime(self.settings)
            child.kill()
            child.wait(timeout=10)
            runtime = HistoricalRuntime(self.settings)
            runtime.close()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            child.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
