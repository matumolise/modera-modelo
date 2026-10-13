"""Aceptación del recorrido ficticio; se ejecuta una vez y se coteja su traza."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.validation.verify_analytics_integrated_path import run


class IntegratedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory()
        cls.output=Path(cls.temp.name)/"integrated"
        cls.report=run(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def case(self,name):
        return json.loads((self.output/name/"result.json").read_text(encoding="utf-8"))

    def test_increase_update_and_return_use_one_card(self):
        case=self.case("increase_return")
        results=[x["response"] for x in case["message_evaluations"]]
        self.assertEqual([r["status"] for r in results],["ACTIVE","INCONCLUSIVE","RESOLVED"])
        self.assertEqual([r["card_version"] for r in results],[1,2,3])
        self.assertEqual(len({r["card"]["card_id"] for r in results}),1)

    def test_decrease_has_symmetric_return(self):
        case=self.case("decrease_return")
        self.assertEqual(case["message_evaluations"][0]["response"]["card"]["direction"],"DECREASE")
        self.assertEqual(case["message_evaluations"][-1]["response"]["status"],"RESOLVED")

    def test_missing_day_stays_null_abstains_and_prevents_card(self):
        case=self.case("missing_day"); day=case["daily_trace"][10]
        self.assertIsNone(day["message_day"]["minutes"])
        self.assertFalse(day["message_day"]["quality_verified"])
        self.assertEqual(day["historical_receipt"]["result"]["evaluation"]["outcome"],"ABSTAIN")
        self.assertEqual(case["message_evaluations"][0]["response"]["status"],"INSUFFICIENT_DATA")

    def test_successful_preparation_does_not_grant_quality(self):
        case=self.case("quality_withheld"); day=case["daily_trace"][20]
        self.assertEqual(day["historical_request"]["representation"]["status"],"OBSERVED")
        self.assertFalse(day["message_day"]["quality_verified"])
        self.assertEqual(case["card_history"]["versions"],[])

    def test_all_daily_traces_keep_identity_and_raw_hashes(self):
        for summary in self.report["summary"]:
            case=self.case(summary["case"])
            for day in case["daily_trace"]:
                rep=day["historical_request"]["representation"]
                self.assertEqual(rep["subject_id"],case["series_id"])
                self.assertIsNone(rep["coverage"]["value"])
                self.assertFalse(day["lineage"]["physical_capture_verified"])
                self.assertFalse(day["lineage"]["coverage_quantified"])

    def test_recreated_runtimes_replay_originals_without_duplicate_cards(self):
        self.assertEqual(self.report["restart_replay_historical_requests"],140)
        self.assertEqual(self.report["restart_replay_message_requests"],8)
        self.assertEqual(self.report["continuity_restarts_before_new_days"],4)
        for summary in self.report["summary"]:
            case=self.case(summary["case"])
            self.assertTrue(case["historical_store_bytes_unchanged"])
            self.assertTrue(case["message_replay_original"])
            self.assertTrue(case["card_history_unchanged_after_replay"])
            self.assertTrue(case["message_store_records_unchanged"])

    def test_message_evidence_points_to_the_same_series_evaluations(self):
        for summary in self.report["summary"]:
            case=self.case(summary["case"])
            known={e["historical_receipt"]["result"]["evaluation"]["evaluation_id"] for e in case["daily_trace"]}
            for entry in case["message_evaluations"]:
                self.assertTrue(set(entry["response"]["c1_evidence_ids"]).issubset(known))
                self.assertEqual(entry["request"]["series_id"],case["series_id"])


if __name__=="__main__": unittest.main()
