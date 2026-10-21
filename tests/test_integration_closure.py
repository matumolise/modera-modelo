"""Contraejemplos de auditoría; datos ficticios y perfil no calibrado."""

from copy import deepcopy
from datetime import timedelta, datetime
from hashlib import sha256
import itertools
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from analytics_service.daily_delivery import assess_daily_plan, PLAN_SCHEMA
from analytics_service.f12_export import prepare_android_export
from analytics_service.historical_api import parse_historical_request, InvalidHistoricalRequest
from analytics_service.http import create_app
from analytics_service.settings import Settings
from analytics_service.condition_mapping import resolve_considerations
from analytics_service.activities import select_activities, InvalidSelection
from tests.test_f12_export_integration import synthetic_export, encode, ROOT, HEADERS, TOKEN
from tests.test_historical_api import body
from tools.integration.verify_f12_phone_parity import load_packet


def ready(day="2026-09-01", minutes=60):
    b, s, rows = synthetic_export(day, minutes)
    return b, prepare_android_export(b, [encode(s, rows)])["request"]


def plan(days):
    b, _ = ready()
    return {"plan_schema": PLAN_SCHEMA, "series": b["series"], "days": days}


def entry(day, state="EXPORT_READY"):
    b, request = ready(day)
    if state == "EXPORT_PENDING": request = None
    if state == "ABSENCE_CONFIRMED": request = prepare_android_export(b, [])["request"]
    return {"local_date": day, "evidence_state": state, "request": request}


class HistoricalSemanticGuardTests(unittest.TestCase):
    def test_impossible_duration_and_open_interval_rejected_before_writing(self):
        with TemporaryDirectory() as d:
            settings = Settings(token=TOKEN, historical_enabled=True,
                                historical_config_path=ROOT / "tests/fixtures/historical_c1_smoke_only.json",
                                historical_repository_path=Path(d) / "state/history.json")
            with TestClient(create_app(settings)) as client:
                for change in ({"value": 1440.001}, {"computed_at": "2026-09-01T00:00:00Z"}):
                    payload = body();payload["representation"].update(change)
                    response = client.post("/v1/historical/evaluate", json=payload, headers=HEADERS)
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertFalse(settings.historical_repository_path.exists())
                    self.assertEqual(client.get("/health").status_code, 200)

    def test_maximum_and_non24h_bounds_follow_interval_not_fixed1440(self):
        for hours in (23, 24, 25):
            payload = body();rep = payload["representation"]
            end = datetime.fromisoformat(rep["interval_start"]) + timedelta(hours=hours)
            rep.update(interval_end=end.isoformat(), computed_at=end.isoformat(), value=hours * 60)
            parse_historical_request(payload)
            rep["value"] += .001
            with self.assertRaises(InvalidHistoricalRequest):parse_historical_request(payload)


class OverlapConsistencyTests(unittest.TestCase):
    def test_empty_or_truncated_overlapping_success_is_not_hidden(self):
        b, s, rows = synthetic_export()
        for selected in ([], rows[:2]):
            s2 = {**s, "collectorRunId": str(uuid4()), "eventCount": len(selected)}
            rows2 = [{**r, "collectorRunId": s2["collectorRunId"], "queryOrdinal": n}
                     for n, r in enumerate(selected)]
            with self.assertRaisesRegex(ValueError, "discrepan"):
                prepare_android_export(b, [encode(s, rows), encode(s2, rows2)])

    def test_intersection_only_and_enum_ordinals_not_used_as_event_identity(self):
        b, s, rows = synthetic_export()
        s2 = {**s, "collectorRunId": str(uuid4()), "requestedBeginEpochMs": rows[1]["eventTimeEpochMs"], "eventCount": 2}
        rows2 = [{**r, "collectorRunId": s2["collectorRunId"], "queryBeginEpochMs": s2["requestedBeginEpochMs"],
                  "queryOrdinal": n} for n, r in enumerate(rows[1:])]
        result = prepare_android_export(b, [encode(s, rows), encode(s2, rows2)])
        self.assertEqual(result["request"]["representation"]["value"], 60)
        self.assertEqual(len(result["preparation"]["raw_events"]), 5)

    def test_failed_query_does_not_claim_an_empty_successful_snapshot(self):
        b, s, rows = synthetic_export()
        failed = {**s, "collectorRunId": str(uuid4()), "eventCount": 0,
                  "usageAccessAvailable": False, "errorCode": "USAGE_ACCESS_NOT_GRANTED", "errorMessage": "no"}
        result = prepare_android_export(b, [encode(s, rows), encode(failed, [])])
        self.assertEqual(result["request"]["representation"]["value"], 60)

    def test_repeated_event_multiplicity_disagreement_rejected_and_budget_bounded(self):
        from unittest.mock import patch
        b, s, rows = synthetic_export()
        s2 = {**s, "collectorRunId": str(uuid4()), "eventCount": 4}
        rows2 = [{**r, "collectorRunId": s2["collectorRunId"]} for r in rows]
        rows2.insert(2, {**rows2[1], "queryOrdinal": 3})
        with self.assertRaisesRegex(ValueError, "discrepan"):
            prepare_android_export(b, [encode(s, rows), encode(s2, rows2)])
        s2["eventCount"] = 3;rows2 = [{**r, "collectorRunId": s2["collectorRunId"]} for r in rows]
        with patch("analytics_service.f12_export.MAX_OVERLAP_COMPARISONS", 0):
            with self.assertRaisesRegex(ValueError, "presupuesto"):
                prepare_android_export(b, [encode(s, rows), encode(s2, rows2)])


class DailyClosureTests(unittest.TestCase):
    def test_pending_blocks_later_days_without_materializing_missing(self):
        result = assess_daily_plan(plan([entry("2026-09-03"), entry("2026-09-01"),
                                        entry("2026-09-02", "EXPORT_PENDING")]))
        self.assertEqual([r["decision"] for r in result["decisions"]],
                         ["READY_TO_FREEZE", "WAIT_FOR_EVIDENCE", "WAIT_FOR_PRECEDING_DAY"])
        self.assertFalse(result["payload_persisted"])
        self.assertFalse(result["http_sent"])

    def test_confirmed_absence_is_missing_and_releases_only_declared_days(self):
        result = assess_daily_plan(plan([entry("2026-09-01", "ABSENCE_CONFIRMED"), entry("2026-09-03")]))
        self.assertEqual([r["decision"] for r in result["decisions"]], ["READY_TO_FREEZE"] * 2)
        self.assertFalse(result["missing_dates_inferred"])
        self.assertEqual(len(result["decisions"]), 2)

    def test_wrong_identity_date_missing_fingerprint_and_unknown_states_rejected(self):
        for mutate in (lambda p:p["days"][0].update(evidence_state="unknown"),
                       lambda p:p["days"][0]["request"]["representation"].update(subject_id="other"),
                       lambda p:p["days"][0].update(local_date="2026-09-02"),
                       lambda p:p["days"][0]["request"]["representation"]["provenance"].update(input_fingerprint=None),
                       lambda p:p["days"].append(deepcopy(p["days"][0]))):
            p = plan([entry("2026-09-01")]);mutate(p)
            with self.assertRaises(ValueError):assess_daily_plan(p)

    def test_pending_cannot_have_final_payload_and_absence_cannot_have_positive_value(self):
        for state in ("EXPORT_PENDING", "ABSENCE_CONFIRMED"):
            p = plan([entry("2026-09-01")]);p["days"][0]["evidence_state"] = state
            with self.assertRaises(ValueError):assess_daily_plan(p)

    def test_cli_is_offline_and_output_is_exclusive(self):
        with TemporaryDirectory() as d:
            source, output = Path(d) / "plan.json", Path(d) / "out.json"
            source.write_text(json.dumps(plan([entry("2026-09-01", "EXPORT_PENDING")])))
            args = [sys.executable, str(ROOT / "tools/integration/check_daily_delivery_plan.py"),
                    "--input", str(source), "--output", str(output)]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), saved)


class PacketIntegrityTests(unittest.TestCase):
    def test_packet_change_between_manifest_and_load_is_not_silently_accepted(self):
        from unittest.mock import patch
        from tools.integration import verify_f12_phone_parity as verifier
        with TemporaryDirectory() as d:
            b, s, rows = synthetic_export();root = Path(d)
            (root / "b.json").write_text(json.dumps(b));x, y = encode(s, rows)
            (root / "s.json").write_bytes(x);(root / "e.jsonl").write_bytes(y)
            result = subprocess.run([sys.executable, str(ROOT / "tools/integration/build_historical_request_from_export.py"),
                                    "--binding", str(root / "b.json"), "--run", str(root / "s.json"), str(root / "e.jsonl"),
                                    "--output-dir", str(root / "packet")], capture_output=True)
            self.assertEqual(result.returncode, 0)
            original_check = verifier._verify_packet_manifest
            def change_after_verification(packet):
                expected = original_check(packet)
                path = packet / "binding.original.json"
                path.write_bytes(path.read_bytes() + b"\n")  # Mismo JSON, bytes distintos.
                return expected
            with patch.object(verifier, "_verify_packet_manifest", change_after_verification):
                with self.assertRaisesRegex(ValueError, "durante la lectura"):
                    load_packet(root / "packet")

    def test_complete_packet_loads_and_intermediate_tampering_is_rejected(self):
        with TemporaryDirectory() as d:
            b, s, rows = synthetic_export();root = Path(d)
            (root / "b.json").write_text(json.dumps(b));x, y = encode(s, rows)
            (root / "s.json").write_bytes(x);(root / "e.jsonl").write_bytes(y)
            argv = [sys.executable, str(ROOT / "tools/integration/build_historical_request_from_export.py"),
                    "--binding", str(root / "b.json"), "--run", str(root / "s.json"), str(root / "e.jsonl"),
                    "--output-dir", str(root / "packet")]
            completed = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            packet = root / "packet";load_packet(packet)
            prep = json.loads((packet / "preparation.json").read_text());prep["schema_version"] = True
            (packet / "preparation.json").write_text(json.dumps(prep))
            with self.assertRaises(ValueError):load_packet(packet)
            # Recalcular hashes no autentica una preparación coherente con raw.
            paths = [p for p in packet.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"]
            (packet / "SHA256SUMS.txt").write_text("".join(sha256(p.read_bytes()).hexdigest() + "  "
                                                   + p.relative_to(packet).as_posix() + "\n" for p in paths))
            with self.assertRaisesRegex(ValueError, "alterado"):load_packet(packet)

    def test_manifest_traversal_and_missing_manifest_do_not_read_another_path(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(OSError):load_packet(root)
            (root / "SHA256SUMS.txt").write_text("0" * 64 + "  ../secret.json\n")
            with self.assertRaises(ValueError):load_packet(root)


class ConditionsCombinationsTests(unittest.TestCase):
    def test_review_matrix_covers_exact_catalog_without_implying_approval(self):
        from recommendations import ACTIVITY_CATALOG
        matrix = json.loads((ROOT / "docs/integration/CATALOG_FUNCTIONAL_REVIEW_V2.json").read_text(encoding="utf-8"))
        self.assertFalse(matrix["automatic_condition_to_filter_mapping"])
        self.assertFalse(matrix["clinical_safety_validated"])
        indexed = {r["activity_id"]: r for r in matrix["activities"]}
        self.assertEqual(set(indexed), {a.activity_id for a in ACTIVITY_CATALOG})
        for a in ACTIVITY_CATALOG:
            row = indexed[a.activity_id]
            self.assertEqual(row["title"], a.title)
            self.assertEqual(row["title_sha256"], sha256(a.title.encode()).hexdigest())
            self.assertEqual(row["description"], a.description)
            self.assertEqual(row["description_sha256"], sha256(a.description.encode()).hexdigest())
            self.assertEqual(row["professional_approval"], "PENDING")
            self.assertEqual(row["runtime_compatibility"], "UNKNOWN")
        self.assertEqual(indexed["social_story_01"]["review_domains"]["auditory"], "E")
        for activity in ("reading_choose_01", "reading_favorite_01"):
            self.assertEqual(indexed[activity]["review_domains"]["visual"], "V")
        for activity in ("creative_character_01", "free_play_build_01", "quiet_draw_01"):
            self.assertEqual(indexed[activity]["review_domains"]["mobility_arms_hands"], "V")
        # Las consignas revisadas no exigen dibujar la historia ni mover las piernas.
        # N describe el texto y no acredita compatibilidad de una persona.
        self.assertEqual(indexed["creative_story_01"]["review_domains"]["mobility_arms_hands"], "N")
        self.assertEqual(indexed["movement_sequence_01"]["review_domains"]["mobility_legs"], "N")

    def test_all_31_valid_nonempty_label_combinations_abstain_without_functional_mapping(self):
        count = 0
        for mobility in (None, "mobility_arms_hands", "mobility_legs", "mobility_both"):
            for toggles in itertools.product((False, True), repeat=3):
                conditions = ([mobility] if mobility else []) + [c for c, use in
                    zip(("visual", "auditory", "sensory"), toggles) if use]
                if not conditions:continue
                resolved = resolve_considerations({"request_id": "matrix", "considerations_state": "known", "conditions": conditions})
                self.assertEqual(resolved["eligibility_state"], "unknown")
                self.assertNotIn("eligibility", resolved)
                result = select_activities({"request_id": "matrix", "context": "voluntary", "eligibility_state": "unknown"})
                self.assertEqual(result["activities"], [])
                count += 1
        self.assertEqual(count, 31)

    def test_none_combined_multiple_mobility_and_empty_known_are_invalid(self):
        for conditions in (["none", "visual"], ["mobility_legs", "mobility_both"], []):
            with self.assertRaises(InvalidSelection):
                resolve_considerations({"request_id": "matrix", "considerations_state": "known", "conditions": conditions})
