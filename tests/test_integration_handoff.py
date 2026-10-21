"""Contrato candidato: datos fabricados, sin validación de captura o clínica."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from analytics_service.activities import CATALOG_VERSION, InvalidSelection, select_activities
from analytics_service.condition_mapping import resolve_considerations
from analytics_service.f12_bridge import build_f12_request, _midnight, _zone
from analytics_service.http import create_app
from analytics_service.settings import Settings
from recommendations import ACTIVITY_CATALOG

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "integration-tests-only-20261012"
HEADERS = {"Authorization": "Bearer " + TOKEN}


def raw_fixture(day="2026-09-01", minutes=60):
    zone = _zone("America/Argentina/Buenos_Aires")
    begin = _midnight(datetime.fromisoformat(day).date(), zone)
    end = begin + timedelta(days=1)
    query_begin = int((begin - timedelta(hours=1)).timestamp() * 1000)
    query_end = int(end.timestamp() * 1000)
    collected = query_end + 60000
    rows = []
    stamps = [(begin - timedelta(minutes=30), 16, "SCREEN_NON_INTERACTIVE")]
    if minutes:
        stamps += [(begin + timedelta(hours=10), 15, "SCREEN_INTERACTIVE"),
                   (begin + timedelta(hours=10, minutes=minutes), 16, "SCREEN_NON_INTERACTIVE")]
    for ordinal, (instant, code, name) in enumerate(stamps):
        rows.append({"schema_version": "raw-usage-event-v1", "collector_run_id": "run-" + day,
                     "query_begin_epoch_ms": query_begin, "query_end_epoch_ms": query_end,
                     "collected_at_epoch_ms": collected, "event_time_epoch_ms": int(instant.timestamp() * 1000),
                     "event_type_code": code, "event_type_name": name, "query_ordinal": ordinal})
    return {"schema_version": 1, "request_id": "fixture-" + day,
            "series": {"profile_id": "profile-test", "device_id": "device-test",
                       "assignment_id": "assignment-test", "time_zone": "America/Argentina/Buenos_Aires",
                       "measurement_version": "capture-test-v1"},
            "local_date": day, "computed_at": (end + timedelta(minutes=2)).isoformat(),
            "raw_events": rows,
            "summaries": [{"collector_run_id": "run-" + day,
                           "requested_begin_epoch_ms": query_begin, "requested_end_epoch_ms": query_end,
                           "collected_at_epoch_ms": collected, "usage_access_available": True,
                           "query_returned_null": False, "event_count": len(rows),
                           "error_code": None, "error_message": None}]}


class F12BridgeTests(unittest.TestCase):
    def test_real_adapter_produces_valid_v2_minutes_and_unknown_coverage(self):
        result = build_f12_request(raw_fixture())["representation"]
        self.assertEqual(result["value"], 60)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["representation_spec_id"], "daily_use_duration_minutes_v2")
        self.assertIsNone(result["coverage"]["value"])
        self.assertEqual(result["interval_start"], "2026-09-01T03:00:00+00:00")

    def test_observed_zero_requires_evidence(self):
        source = raw_fixture(minutes=0)
        self.assertEqual(build_f12_request(source)["representation"]["status"], "OBSERVED_ZERO")
        source["raw_events"] = []
        source["summaries"][0]["event_count"] = 0
        result = build_f12_request(source)["representation"]
        self.assertEqual(result["status"], "MISSING")
        self.assertIsNone(result["value"])

    def test_failed_permission_does_not_become_zero(self):
        source = raw_fixture(minutes=0)
        source["raw_events"] = []
        source["summaries"][0].update(event_count=0, usage_access_available=False)
        self.assertEqual(build_f12_request(source)["representation"]["status"], "MISSING")

    def test_partial_capture_is_missing(self):
        source = raw_fixture()
        source["summaries"][0]["requested_end_epoch_ms"] -= 3600000
        for row in source["raw_events"]:
            row["query_end_epoch_ms"] -= 3600000
        self.assertEqual(build_f12_request(source)["representation"]["status"], "MISSING")

    def test_identity_splits_every_binding_dimension(self):
        source = raw_fixture()
        original = build_f12_request(source)["representation"]["subject_id"]
        for field in ("profile_id", "device_id", "assignment_id", "measurement_version"):
            with self.subTest(field=field):
                changed = deepcopy(source)
                changed["series"][field] += "-changed"
                self.assertNotEqual(build_f12_request(changed)["representation"]["subject_id"], original)
        changed = deepcopy(source)
        changed["series"]["time_zone"] = "UTC"
        self.assertNotEqual(build_f12_request(changed)["representation"]["subject_id"], original)

    def test_reordering_keeps_payload_and_processing_time_does_not_change_identity(self):
        source = raw_fixture()
        original = build_f12_request(source)
        source["raw_events"].reverse()
        self.assertEqual(build_f12_request(source), original)
        source["computed_at"] = "2026-10-01T03:00:00Z"
        retry = build_f12_request(source)
        for field in ("subject_id", "representation_record_id", "provenance"):
            self.assertEqual(retry["representation"][field], original["representation"][field])

    def test_revised_evidence_keeps_record_identity_and_changes_fingerprint(self):
        source = raw_fixture()
        original = build_f12_request(source)["representation"]
        source["raw_events"][-1]["event_time_epoch_ms"] += 60000
        changed = build_f12_request(source)["representation"]
        self.assertEqual(changed["representation_record_id"], original["representation_record_id"])
        self.assertNotEqual(changed["provenance"], original["provenance"])

    def test_code_name_mismatch_and_boolean_epoch_are_rejected(self):
        for change in ({"event_type_code": 15}, {"event_time_epoch_ms": True}):
            source = raw_fixture()
            source["raw_events"][0].update(change)
            with self.assertRaises(ValueError):
                build_f12_request(source)

    def test_bad_run_counts_and_duplicate_ordinals_are_rejected(self):
        source = raw_fixture()
        source["summaries"][0]["event_count"] += 1
        with self.assertRaises(ValueError):
            build_f12_request(source)
        source = raw_fixture()
        source["raw_events"][1]["query_ordinal"] = 0
        with self.assertRaises(ValueError):
            build_f12_request(source)

    def test_contradictory_screen_state_at_same_instant_is_rejected(self):
        source = raw_fixture()
        source["raw_events"][-1]["event_time_epoch_ms"] = source["raw_events"][1]["event_time_epoch_ms"]
        with self.assertRaises(ValueError):
            build_f12_request(source)

    def test_reboot_does_not_create_artificial_continuity(self):
        source = raw_fixture()
        row = deepcopy(source["raw_events"][1])
        row.update(event_type_code=27, event_type_name="DEVICE_STARTUP", query_ordinal=3)
        source["raw_events"].append(row)
        source["summaries"][0]["event_count"] += 1
        result = build_f12_request(source)["representation"]
        self.assertEqual(result["status"], "MISSING")
        self.assertIn("DEVICE_LIFECYCLE_REVIEW_REQUIRED", result["quality_flags"])

    def test_open_day_and_clock_inconsistency_are_rejected(self):
        source = raw_fixture()
        source["computed_at"] = "2026-09-01T20:00:00Z"
        with self.assertRaises(ValueError):
            build_f12_request(source)
        source = raw_fixture()
        source["summaries"][0]["collected_at_epoch_ms"] += 9999999
        with self.assertRaises(ValueError):
            build_f12_request(source)

    def test_day_lengths_are_not_assumed_24_hours(self):
        zone = _zone("America/New_York")
        for day, hours in (("2026-03-08", 23), ("2026-11-01", 25)):
            start = datetime.fromisoformat(day).date()
            self.assertEqual((_midnight(start + timedelta(days=1), zone) - _midnight(start, zone)).total_seconds(), hours * 3600)

    def test_invalid_timezone_and_nonexistent_midnight_fail_explicitly(self):
        with self.assertRaises(ValueError):
            _zone("../UTC")
        with self.assertRaises(ValueError):
            _midnight(datetime(2011, 12, 30).date(), _zone("Pacific/Apia"))

    def test_cli_is_offline_and_refuses_overwrite(self):
        with TemporaryDirectory() as directory:
            source, output = Path(directory) / "source.json", Path(directory) / "request.json"
            source.write_text(json.dumps(raw_fixture()), encoding="utf-8")
            args = [sys.executable, str(ROOT / "tools/integration/build_historical_request.py"),
                    "--input", str(source), "--output", str(output)]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)

    def test_bridge_payload_persists_replays_and_conflicts_through_api(self):
        with TemporaryDirectory() as directory:
            settings = Settings(token=TOKEN, historical_enabled=True,
                                historical_config_path=ROOT / "tests/fixtures/historical_c1_smoke_only.json",
                                historical_repository_path=Path(directory) / "history.json")
            source = raw_fixture()
            payload = build_f12_request(source)
            with TestClient(create_app(settings)) as client:
                first = client.post("/v1/historical/evaluate", headers=HEADERS, json=payload)
                self.assertEqual(first.status_code, 200)
                original = first.json()["result"]
            with TestClient(create_app(settings)) as client:
                retry = client.post("/v1/historical/evaluate", headers=HEADERS, json=payload)
                self.assertTrue(retry.json()["replayed"])
                self.assertEqual(retry.json()["result"], original)
                source["raw_events"][-1]["event_time_epoch_ms"] += 60000
                self.assertEqual(client.post("/v1/historical/evaluate", headers=HEADERS,
                                             json=build_f12_request(source)).status_code, 409)


class ConsiderationsTests(unittest.TestCase):
    def request(self, state="known", conditions=None):
        result = {"request_id": "form-test", "considerations_state": state}
        if conditions is not None:
            result["conditions"] = conditions
        return result

    def test_none_is_explicit_and_preserves_original_selector(self):
        result = resolve_considerations(self.request(conditions=["none"]))
        self.assertEqual(result["eligibility_state"], "known")
        selected = select_activities({"request_id": "windows-smoke-01", "context": "voluntary",
                                      "eligibility_state": result["eligibility_state"],
                                      "eligibility": result["eligibility"]})
        # «Ninguna» no debe agregar filtros. La huella incluye el catálogo vigente.
        unfiltered = select_activities({"request_id": "windows-smoke-01", "context": "voluntary",
                                       "eligibility_state": "known", "eligibility": {}})
        self.assertEqual(selected, unfiltered)
        self.assertEqual(selected["selector_version"],
                         "published-selector-sha256:f0c44edc74e0dff72163c593ea56298ce56050cf9aca2fd77c9a3ac6be6f5ace")
        self.assertEqual(len(ACTIVITY_CATALOG), 18)

    def test_every_condition_needs_functional_review(self):
        for condition in ("mobility_arms_hands", "mobility_legs", "mobility_both", "visual", "auditory", "sensory"):
            with self.subTest(condition=condition):
                result = resolve_considerations(self.request(conditions=[condition]))
                self.assertEqual(result["eligibility_state"], "unknown")
                self.assertNotIn("eligibility", result)
                self.assertTrue(result["required_followups"])

    def test_multiple_domains_are_canonical_and_do_not_erase_each_other(self):
        a = resolve_considerations(self.request(conditions=["visual", "mobility_both", "sensory"]))
        b = resolve_considerations(self.request(conditions=["sensory", "mobility_both", "visual"]))
        self.assertEqual(a, b)
        self.assertEqual(len(a["required_followups"]), 5)

    def test_unknown_omission_empty_and_contradictions_are_distinct(self):
        result = resolve_considerations(self.request("unknown"))
        self.assertEqual(result["eligibility_state"], "unknown")
        for conditions in (None, [], ["none", "visual"], ["visual", "visual"],
                           ["mobility_legs", "mobility_both"], ["new-diagnosis"]):
            with self.subTest(conditions=conditions):
                with self.assertRaises(InvalidSelection):
                    resolve_considerations(self.request(conditions=conditions))
        with self.assertRaises(InvalidSelection):
            resolve_considerations(self.request("unknown", []))

    def test_http_auth_disabled_and_contract(self):
        with TestClient(create_app(Settings(token=TOKEN))) as client:
            path = "/v1/activities/eligibility"
            self.assertEqual(client.post(path, json=self.request(conditions=["none"])).status_code, 401)
            self.assertEqual(client.post(path, headers=HEADERS, json=self.request(conditions=[])).status_code, 400)
            response = client.post(path, headers=HEADERS, json=self.request(conditions=["visual"]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["eligibility_state"], "unknown")
            self.assertEqual(response.json()["catalog_version"], CATALOG_VERSION)
        with TestClient(create_app(Settings(token=TOKEN, activities_enabled=False))) as client:
            self.assertEqual(client.post(path, headers=HEADERS, json=self.request(conditions=["none"])).status_code, 503)


if __name__ == "__main__":
    unittest.main()
