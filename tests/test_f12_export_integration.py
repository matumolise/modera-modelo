"""Exports ficticios fieles a DiagnosticExport.kt; ninguna captura física."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import UUID

from fastapi.testclient import TestClient

from analytics_service.f12_bridge import _midnight, _zone
from analytics_service.f12_export import (
    EVENT_FIELDS, SUMMARY_FIELDS, event_name, parse_export_pair, prepare_android_export,
)
from analytics_service.http import create_app
from analytics_service.settings import Settings
from tools.integration.verify_f12_phone_parity import verify
from tests.test_integration_handoff import raw_fixture

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/f12_export"
TOKEN = "export-integration-tests-only"
HEADERS = {"Authorization": "Bearer " + TOKEN}


def synthetic_export(day="2026-09-01", minutes=60):
    projected = raw_fixture(day, minutes)
    run_id = str(UUID(bytes=sha256(day.encode()).digest()[:16], version=4))
    summary = {key: projected["summaries"][0][field] for key, field in SUMMARY_FIELDS.items()}
    summary["collectorRunId"] = run_id
    rows = [{**{key: row[field] for key, field in EVENT_FIELDS.items()},
             "collectorRunId": run_id, "packageName": None, "className": None,
             "androidApiLevel": 35, "manufacturer": "SYNTHETIC", "model": "NOT-A-PHONE"}
            for row in projected["raw_events"]]
    binding = {k: projected[k] for k in projected.keys() - {"raw_events", "summaries"}}
    return binding, summary, rows


def encode(summary, rows):
    return (json.dumps(summary, ensure_ascii=False, indent=2).encode(),
            b"".join(json.dumps(row, ensure_ascii=False).encode() + b"\n" for row in rows))


def prepared(binding, summary, rows):
    return prepare_android_export(binding, [encode(summary, rows)])


class ExportAdapterTests(unittest.TestCase):
    def setUp(self):
        self.binding, self.summary, self.rows = synthetic_export()

    def value(self, summary=None, rows=None):
        return prepared(self.binding, self.summary if summary is None else summary,
                        self.rows if rows is None else rows)["request"]["representation"]

    def test_committed_fixture_is_exact_producer_shape_and_fictitious(self):
        binding = json.loads((FIXTURE / "binding.synthetic.json").read_text())
        pairs = [(FIXTURE.joinpath("observed/summary.json").read_bytes(),
                  FIXTURE.joinpath("observed/events.jsonl").read_bytes())]
        result = prepare_android_export(binding, pairs)
        self.assertEqual(result["request"]["representation"]["value"], 60)
        self.assertFalse(result["audit"]["physical_capture_verified"])
        self.assertEqual(len(json.loads(pairs[0][0])), 9)
        self.assertEqual(len(json.loads(pairs[0][1].splitlines()[0])), 14)

    def test_projection_preserves_counts_and_all_source_rows(self):
        extra = deepcopy(self.rows[-1])
        extra.update(eventTypeCode=7, eventTypeName="USER_INTERACTION", queryOrdinal=3)
        rows = self.rows + [extra]
        summary = {**self.summary, "eventCount": 4}
        result = prepared(self.binding, summary, rows)
        self.assertEqual(len(result["preparation"]["raw_events"]), 4)
        self.assertEqual(result["request"]["representation"]["value"], 60)
        self.assertIsNone(result["request"]["representation"]["coverage"]["value"])

    def test_permission_null_and_exception_states_remain_missing(self):
        for code, available, null, message in (
            ("USAGE_ACCESS_NOT_GRANTED", False, False, "Usage Access is not granted for this app."),
            ("QUERY_RETURNED_NULL", True, True, "UsageStatsManager.queryEvents returned null."),
            ("SECURITY_EXCEPTION", True, False, None),
            ("QUERY_RUNTIME_EXCEPTION", True, False, ""),
        ):
            with self.subTest(code=code):
                summary = {**self.summary, "errorCode": code, "errorMessage": message,
                           "usageAccessAvailable": available, "queryReturnedNull": null, "eventCount": 0}
                value = self.value(summary, [])
                self.assertEqual(value["status"], "MISSING")
                self.assertIsNone(value["value"])

    def test_empty_success_is_missing_but_known_off_can_be_zero(self):
        value = self.value({**self.summary, "eventCount": 0}, [])
        self.assertEqual(value["status"], "MISSING")
        value = self.value({**self.summary, "eventCount": 1}, self.rows[:1])
        self.assertEqual((value["status"], value["value"]), ("OBSERVED_ZERO", 0))

    def test_no_export_is_explicit_missing_without_invented_query_summary(self):
        result = prepare_android_export(self.binding, [])
        self.assertEqual(result["request"]["representation"]["status"], "MISSING")
        self.assertIsNone(result["request"]["representation"]["value"])
        self.assertEqual(result["preparation"]["summaries"], [])
        self.assertEqual(result["audit"]["originals"], [])
        self.assertEqual(result["audit"]["export_evidence_state"], "NO_EXPORT_DECLARED_BY_BACKEND")
        self.assertFalse(result["audit"]["hardware_metadata_available"])

    def test_cli_no_export_requires_flag_and_never_hides_missing_input_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "binding.json").write_text(json.dumps(self.binding))
            command = [sys.executable, str(ROOT / "tools/integration/build_historical_request_from_export.py"),
                       "--binding", str(root / "binding.json"), "--output-dir", str(root / "out")]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertNotEqual(subprocess.run(command + ["--run", str(root / "absent.json"),
                                                         str(root / "absent.jsonl")], capture_output=True).returncode, 0)
            self.assertFalse((root / "out").exists())
            accepted = subprocess.run(command + ["--no-export"], capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            payload = json.loads((root / "out/request.json").read_text())
            self.assertEqual(payload["representation"]["status"], "MISSING")
            self.assertFalse((root / "out/originals").exists())

    def test_counts_ordinals_schema_and_flags_are_strict(self):
        mutations = [lambda s, r: s.update(eventCount=2),
                     lambda s, r: r[1].update(queryOrdinal=0),
                     lambda s, r: r[2].update(queryOrdinal=10),
                     lambda s, r: r[0].update(schemaVersion="v9"),
                     lambda s, r: s.update(usageAccessAvailable=False),
                     lambda s, r: s.update(queryReturnedNull=True),
                     lambda s, r: s.update(errorCode="UNKNOWN"),
                     lambda s, r: r[0].update(androidApiLevel=True),
                     lambda s, r: r[0].update(eventTimeEpochMs=True),
                     lambda s, r: s.update(eventCount=True),
                     lambda s, r: r[0].update(packageName=42),
                     lambda s, r: s.update(errorMessage="unexpected")]
        for mutate in mutations:
            s, r = deepcopy(self.summary), deepcopy(self.rows)
            mutate(s, r)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.value(s, r)

    def test_swapped_summary_clock_and_query_bounds_rejected(self):
        for change in ({"collectorRunId": str(UUID(int=2, version=4))},
                       {"queryEndEpochMs": self.summary["requestedEndEpochMs"] + 1},
                       {"collectedAtEpochMs": self.summary["collectedAtEpochMs"] + 1}):
            rows = deepcopy(self.rows)
            rows[0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.value(rows=rows)
        with self.assertRaises(ValueError):
            self.value({**self.summary, "collectedAtEpochMs": self.summary["requestedEndEpochMs"] - 1})

    def test_export_order_not_repaired_but_ordinals_can_reflect_enumeration_order(self):
        with self.assertRaises(ValueError):
            self.value(rows=list(reversed(self.rows)))
        rows = deepcopy(self.rows)
        rows[0]["queryOrdinal"], rows[1]["queryOrdinal"] = 1, 0
        self.assertEqual(self.value(rows=rows)["value"], 60)

    def test_non_finite_duplicate_keys_blank_lines_and_missing_fields_rejected(self):
        summary, events = encode(self.summary, self.rows)
        for s, e in ((summary[:-1] + b',"eventCount":3}', events),
                     (summary, events + b"\n"), (summary, b"NaN\n"),
                     (summary, events.replace(b'"packageName": null, ', b"", 1))):
            with self.subTest(data=e[:40]), self.assertRaises(ValueError):
                parse_export_pair(s, e)

    def test_mapper_matches_android_28_and_modern_aliases_and_fallback(self):
        self.assertEqual(event_name(1, 28), "MOVE_TO_FOREGROUND")
        self.assertEqual(event_name(1, 29), "ACTIVITY_RESUMED")
        self.assertEqual(event_name(27, 28), "EVENT_TYPE_27")
        self.assertEqual(event_name(12345, 35), "EVENT_TYPE_12345")
        rows = deepcopy(self.rows)
        rows[0]["eventTypeName"] = "SCREEN_INTERACTIVE"
        with self.assertRaises(ValueError):
            self.value(rows=rows)

    def test_metadata_changes_and_raw_whitespace_change_provenance(self):
        pair = encode(self.summary, self.rows)
        original = prepare_android_export(self.binding, [pair])["request"]["representation"]
        rows = deepcopy(self.rows)
        rows[1]["packageName"] = "ar.synthetic.changed"
        changed = self.value(rows=rows)
        self.assertEqual(changed["value"], original["value"])
        self.assertNotEqual(changed["provenance"], original["provenance"])
        changed = prepare_android_export(self.binding, [(pair[0] + b"\n", pair[1])])["request"]["representation"]
        self.assertNotEqual(changed["provenance"], original["provenance"])

    def test_two_devices_cannot_be_combined_using_model_metadata(self):
        rows = deepcopy(self.rows)
        rows[1]["model"] = "OTHER"
        with self.assertRaises(ValueError):
            self.value(rows=rows)

    def test_gaps_remain_missing_and_overlap_is_not_double_counted(self):
        first = deepcopy(self.summary)
        cut = self.rows[1]["eventTimeEpochMs"]
        first["requestedEndEpochMs"] = cut
        first["eventCount"] = 1
        rows1 = deepcopy(self.rows[:1])
        rows1[0]["queryEndEpochMs"] = cut
        second = deepcopy(self.summary)
        second["collectorRunId"] = str(UUID(int=22, version=4))
        second["requestedBeginEpochMs"] = cut + 1
        second["eventCount"] = 1
        rows2 = deepcopy(self.rows[2:])
        rows2[0].update(collectorRunId=second["collectorRunId"], queryBeginEpochMs=cut + 1, queryOrdinal=0)
        gap = prepare_android_export(self.binding, [encode(first, rows1), encode(second, rows2)])
        self.assertEqual(gap["request"]["representation"]["status"], "MISSING")
        second = deepcopy(self.summary)
        second["collectorRunId"] = str(UUID(int=23, version=4))
        rows2 = [{**row, "collectorRunId": second["collectorRunId"]} for row in self.rows]
        overlap = prepare_android_export(self.binding, [encode(self.summary, self.rows), encode(second, rows2)])
        self.assertEqual(overlap["request"]["representation"]["value"], 60)
        self.assertEqual(len(overlap["preparation"]["raw_events"]), 6)
        reverse = prepare_android_export(self.binding, [encode(second, rows2), encode(self.summary, self.rows)])
        self.assertEqual(reverse["request"], overlap["request"])

    def test_repeat_same_query_rejected_repeated_events_retained(self):
        pair = encode(self.summary, self.rows)
        with self.assertRaises(ValueError):
            prepare_android_export(self.binding, [pair, pair])
        rows = deepcopy(self.rows)
        rows.insert(2, {**rows[1], "queryOrdinal": 3})
        summary = {**self.summary, "eventCount": 4}
        result = prepared(self.binding, summary, rows)
        self.assertEqual(len(result["preparation"]["raw_events"]), 4)
        self.assertEqual(result["request"]["representation"]["value"], 60)

    def test_reboot_and_opposing_same_instant_do_not_create_continuity(self):
        rows = deepcopy(self.rows)
        rows.insert(2, {**rows[1], "eventTypeCode": 27, "eventTypeName": "DEVICE_STARTUP", "queryOrdinal": 3})
        result = self.value({**self.summary, "eventCount": 4}, rows)
        self.assertEqual(result["status"], "MISSING")
        self.assertIn("DEVICE_LIFECYCLE_REVIEW_REQUIRED", result["quality_flags"])
        rows = deepcopy(self.rows)
        rows[-1]["eventTimeEpochMs"] = rows[1]["eventTimeEpochMs"]
        with self.assertRaises(ValueError):
            self.value(rows=rows)

    def test_closed_local_days_dst_and_exclusive_end(self):
        for local_day, zone_name, hours in (("2026-03-08", "America/New_York", 23),
                                           ("2026-11-01", "America/New_York", 25)):
            binding, summary, rows = synthetic_export(local_day, 0)
            zone = _zone(zone_name)
            day = date.fromisoformat(local_day)
            begin, end = _midnight(day, zone), _midnight(day + timedelta(days=1), zone)
            b, e = int(begin.timestamp() * 1000), int(end.timestamp() * 1000)
            binding["series"]["time_zone"] = zone_name
            binding["computed_at"] = (end + timedelta(minutes=2)).isoformat()
            summary.update(requestedBeginEpochMs=b - 3600000, requestedEndEpochMs=e, collectedAtEpochMs=e + 60000)
            rows[0].update(queryBeginEpochMs=b - 3600000, queryEndEpochMs=e,
                           collectedAtEpochMs=e + 60000, eventTimeEpochMs=b - 1800000,
                           eventTypeCode=15, eventTypeName="SCREEN_INTERACTIVE")
            rep = prepared(binding, summary, rows)["request"]["representation"]
            self.assertEqual(rep["value"], hours * 60)
            rows[0]["eventTimeEpochMs"] = e
            with self.assertRaises(ValueError):
                prepared(binding, summary, rows)

    def test_cli_archives_bytes_and_refuses_overwrite_without_touching_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            binding, summary, events, output = [root / name for name in ("binding.json", "summary.json", "events.jsonl", "out")]
            binding.write_text(json.dumps(self.binding))
            pair = encode(self.summary, self.rows)
            summary.write_bytes(pair[0]); events.write_bytes(pair[1])
            argv = [sys.executable, str(ROOT / "tools/integration/build_historical_request_from_export.py"),
                    "--binding", str(binding), "--run", str(summary), str(events), "--output-dir", str(output)]
            result = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            archived = output / "originals" / self.summary["collectorRunId"]
            self.assertEqual((archived / "summary.json").read_bytes(), pair[0])
            self.assertEqual((archived / "events.jsonl").read_bytes(), pair[1])
            before = (output / "request.json").read_bytes()
            self.assertNotEqual(subprocess.run(argv, capture_output=True).returncode, 0)
            self.assertEqual((output / "request.json").read_bytes(), before)
            self.assertEqual(events.read_bytes(), pair[1])
            for line in (output / "SHA256SUMS.txt").read_text().splitlines():
                checksum, name = line.split("  ", 1)
                self.assertEqual(sha256((output / name).read_bytes()).hexdigest(), checksum)

    def test_bad_cli_input_creates_no_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "binding.json").write_text(json.dumps(self.binding))
            (root / "summary.json").write_bytes(encode(self.summary, self.rows)[0])
            (root / "events.jsonl").write_text("{}\n")
            result = subprocess.run([sys.executable, str(ROOT / "tools/integration/build_historical_request_from_export.py"),
                                     "--binding", str(root / "binding.json"), "--run", str(root / "summary.json"),
                                     str(root / "events.jsonl"), "--output-dir", str(root / "out")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "out").exists())

    def test_parity_verifier_checks_same_bytes_and_rejects_false_physical_claim(self):
        # Reporte FICTICIO: prueba el verificador, no ejecuta Kotlin ni teléfono.
        with TemporaryDirectory() as directory:
            packet = Path(directory)
            pair = encode(self.summary, self.rows)
            result = prepare_android_export(self.binding, [pair])
            original = packet / "originals" / self.summary["collectorRunId"]
            original.mkdir(parents=True)
            (original / "summary.json").write_bytes(pair[0]); (original / "events.jsonl").write_bytes(pair[1])
            (packet / "binding.original.json").write_text(json.dumps(self.binding))
            (packet / "lineage.json").write_text(json.dumps(result["audit"]))
            (packet / "request.json").write_text(json.dumps(result["request"]))
            rep = result["request"]["representation"]
            report = {"reportSchema": "f12-phone-parity-v1", "collectorRunId": self.summary["collectorRunId"],
                      "summarySha256": sha256(pair[0]).hexdigest(), "eventsSha256": sha256(pair[1]).hexdigest(),
                      "localDate": self.binding["local_date"], "timeZone": self.binding["series"]["time_zone"],
                      "phoneTimeZone": self.binding["series"]["time_zone"],
                      "intervalBeginEpochMs": int(datetime.fromisoformat(rep["interval_start"]).timestamp() * 1000),
                      "intervalEndEpochMs": int(datetime.fromisoformat(rep["interval_end"]).timestamp() * 1000),
                      "status": "OBSERVED", "durationMs": 3600000, "manualCaptureValidation": "PENDING"}
            self.assertEqual(verify(report, packet)["physical_capture_validation"], "PENDING")
            for change in ({"durationMs": 1}, {"status": "MISSING"}, {"phoneTimeZone": "UTC"},
                           {"intervalEndEpochMs": report["intervalEndEpochMs"] - 1},
                           {"summarySha256": "0" * 64}, {"manualCaptureValidation": "APPROVED"}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    verify({**report, **change}, packet)
            (original / "events.jsonl").write_bytes(pair[1] + b"\n")
            with self.assertRaises(ValueError):
                verify(report, packet)

    def test_export_header_cannot_claim_missing_backend_identity_or_open_day(self):
        for change in ({"computed_at": "2026-09-01T04:00:00Z"}, {"series": {}},
                       {"schema_version": True}, {"local_date": "20260901"}):
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError)):
                prepared({**self.binding, **change}, self.summary, self.rows)

    def test_backend_id_changes_split_stream_but_retry_time_does_not(self):
        original = prepared(self.binding, self.summary, self.rows)["request"]
        retry = prepared({**self.binding, "request_id": "retry", "computed_at": "2026-10-12T00:00:00Z"},
                         self.summary, self.rows)["request"]
        self.assertEqual(original["representation"]["provenance"], retry["representation"]["provenance"])
        binding = deepcopy(self.binding)
        binding["series"]["assignment_id"] += "-replacement"
        changed = prepared(binding, self.summary, self.rows)["request"]
        self.assertNotEqual(original["representation"]["subject_id"], changed["representation"]["subject_id"])

    def test_failed_capture_cannot_include_events_and_hardware_changes_between_queries_rejected(self):
        summary = {**self.summary, "errorCode": "SECURITY_EXCEPTION", "errorMessage": ""}
        with self.assertRaises(ValueError):
            self.value(summary)
        second = {**self.summary, "collectorRunId": str(UUID(int=77, version=4))}
        rows2 = [{**row, "collectorRunId": second["collectorRunId"], "androidApiLevel": 36} for row in self.rows]
        with self.assertRaises(ValueError):
            prepare_android_export(self.binding, [encode(self.summary, self.rows), encode(second, rows2)])


class ExportPersistenceTests(unittest.TestCase):
    def test_export_pipeline_receipt_survives_runtime_restart_and_conflict(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(token=TOKEN, historical_enabled=True,
                                historical_config_path=ROOT / "tests/fixtures/historical_c1_smoke_only.json",
                                historical_repository_path=root / "state/history.json")
            requests, results = [], []
            with TestClient(create_app(settings)) as client:
                for n, minutes in enumerate((90, 100, 110, 100, 400)):
                    binding, summary, rows = synthetic_export("2026-09-0" + str(n + 1), minutes)
                    payload = prepared(binding, summary, rows)["request"]
                    response = client.post("/v1/historical/evaluate", json=payload, headers=HEADERS)
                    self.assertEqual(response.status_code, 200, response.text)
                    requests.append(payload); results.append(response.json()["result"])
                self.assertEqual(results[-1]["evaluation"]["outcome"], "CHANGE")
            # Un nuevo runtime abre el mismo archivo: no depende de caché HTTP.
            with TestClient(create_app(settings)) as client:
                for payload, original in zip(requests, results):
                    retry = deepcopy(payload)
                    retry["request_id"] += "-retry"
                    retry["representation"]["computed_at"] = "2026-10-12T00:00:00Z"
                    response = client.post("/v1/historical/evaluate", json=retry, headers=HEADERS)
                    self.assertTrue(response.json()["replayed"])
                    self.assertEqual(response.json()["result"], original)
                binding, summary, rows = synthetic_export("2026-09-01", 90)
                rows[0]["packageName"] = "ar.synthetic.changed"
                conflict = prepared(binding, summary, rows)["request"]
                response = client.post("/v1/historical/evaluate", json=conflict, headers=HEADERS)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["error"], "representation_conflict")
