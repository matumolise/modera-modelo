"""Ejemplos de aceptación, persistencia y HTTP; sin datos ni modelos reales."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction as Q
from pathlib import Path
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient
from analytics_service.adult_messages import (AdultMessageService, MessageConflict,
    CONFIG, direction, statistics, parse_payload)
from analytics_service.http import create_app
from analytics_service.settings import Settings

TOKEN = "adult-message-fixture-token"
HEADERS = {"Authorization": "Bearer "+TOKEN}
START = date(2026,1,5)


def payload(values, day=28, request="r1", profile="p1", series="s1"):
    return {"request_id":request, "profile_id":profile, "series_id":series,
            "time_zone":"America/Argentina/Buenos_Aires", "evaluation_date":(START+timedelta(days=day)).isoformat(),
            "assignment_verified":True, "shared_phone":False, "context_declared":False,
            "c1_evidence_ids":[], "days":[{"date":(START+timedelta(days=i)).isoformat(),"revision":1,
                "minutes":v,"observed":v is not None,"quality_verified":v is not None} for i,v in enumerate(values)]}


class MessageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/"messages.sqlite3"
        self.service = AdultMessageService(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_increase_text_and_no_delivery_claim(self):
        result = self.service.evaluate(payload([100]*14+[140]*14))
        self.assertEqual((result["status"],result["action"],result["card_version"]),("ACTIVE","CREATE",1))
        self.assertEqual(result["card"]["statistics"]["delta"],40)
        self.assertTrue(result["card"]["recommendation"])
        self.assertEqual(result["card"]["delivery_status"],"CANDIDATE_NOT_DELIVERED")

    def test_open_decrease(self):
        result = self.service.evaluate(payload([140]*14+[100]*14))
        self.assertEqual(result["card"]["direction"],"DECREASE")
        self.assertIn("Menos uso",result["card"]["title"])

    def test_flat_weekly_pattern_and_single_peak_do_not_open(self):
        cases = [[100]*28, [60,70,80,90,100,180,160]*4, [100]*27+[380]]
        for i, values in enumerate(cases):
            with self.subTest(i=i):
                result = self.service.evaluate(payload(values,request=f"r{i}",profile=f"p{i}"))
                self.assertEqual(result["status"],"NO_CARD")

    def test_missing_or_unverified_does_not_become_zero(self):
        p=payload([100]*14+[140]*14); p["days"][20]["quality_verified"]=False
        self.assertEqual(self.service.evaluate(p)["status"],"INSUFFICIENT_DATA")
        q=payload([100]*14+[None]+[140]*13,request="r2",profile="p2")
        self.assertEqual(self.service.evaluate(q)["status"],"INSUFFICIENT_DATA")

    def test_return_keeps_same_card_and_history(self):
        opened=self.service.evaluate(payload([100]*14+[140]*14))
        result=self.service.evaluate(payload([100]*14+[140]*14+[100]*14,42,"r2"))
        self.assertEqual(result["status"],"RESOLVED")
        self.assertEqual(opened["card"]["card_id"],result["card"]["card_id"])
        self.assertEqual([x["version"] for x in self.service.history("p1")],[1,2])

    def test_decrease_return_is_symmetric(self):
        self.service.evaluate(payload([140]*14+[100]*14))
        result=self.service.evaluate(payload([140]*14+[100]*14+[140]*14,42,"r2"))
        self.assertEqual(result["status"],"RESOLVED")

    def test_one_low_day_does_not_resolve(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        result=self.service.evaluate(payload([100]*14+[140]*14+[110]*13+[0],42,"r2"))
        self.assertEqual(result["status"],"INCONCLUSIVE")

    def test_overlap_not_resolved(self):
        self.service.evaluate(payload([100]*14+[125]*14))
        # Siete días aún altos y siete ceros: bajo el margen, pero solapa apertura.
        result=self.service.evaluate(payload([100]*14+[125]*14+[0]*7,35,"r2"))
        self.assertEqual(result["status"],"INCONCLUSIVE")

    def test_replay_after_restart_and_semantic_duplicate(self):
        p=payload([100]*14+[140]*14); a=self.service.evaluate(p)
        self.service=AdultMessageService(self.path)
        b=self.service.evaluate(p)
        self.assertTrue(b["replayed"])
        self.assertEqual({k:v for k,v in a.items() if k!="replayed"},{k:v for k,v in b.items() if k!="replayed"})
        p["request_id"]="another"; p["days"].reverse()
        self.assertTrue(self.service.evaluate(p)["replayed"])
        self.assertEqual(len(self.service.history("p1")),1)

    def test_same_request_different_content_conflicts(self):
        p=payload([100]*14+[140]*14); self.service.evaluate(p)
        p["days"][0]["minutes"]=101
        with self.assertRaises(MessageConflict): self.service.evaluate(p)

    def test_revision_conflict_and_atomic_rollback(self):
        p=payload([100]*14+[140]*14); self.service.evaluate(p)
        q=deepcopy(p); q["request_id"]="r2"; q["days"][0]["revision"]=2
        q["days"][0]["minutes"]=101; q["days"][1]["minutes"]=102
        with self.assertRaises(MessageConflict): self.service.evaluate(q)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT MAX(revision) FROM revisions WHERE day=?",(START.isoformat(),)).fetchone()[0],1)

    def test_corrected_opening_withdraws_and_preserves_original(self):
        p=payload([100]*14+[140]*14); self.service.evaluate(p)
        q=payload([100]*28,28,"r2")
        for row in q["days"][14:]: row["revision"]=2
        result=self.service.evaluate(q)
        self.assertEqual(result["status"],"WITHDRAWN")
        self.assertIsNotNone(result["c1_correction_warning_since"])
        self.assertEqual(self.service.history("p1")[0]["card"]["status"],"ACTIVE")
        self.assertEqual(self.service.evaluate(p)["card"]["status"],"ACTIVE")

    def test_closed_card_correction_archived_not_reopened(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        self.service.evaluate(payload([100]*14+[140]*14+[100]*14,42,"r2"))
        q=payload([100]*42,42,"r3")
        for row in q["days"][14:28]: row["revision"]=2
        result=self.service.evaluate(q)
        self.assertEqual(result["status"],"COOLDOWN")
        self.assertEqual(result["historical_card_corrections"][0]["status"],"WITHDRAWN")
        self.assertEqual(len(self.service.history("p1")),3)

    def test_revisions_remain_available_for_audit(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        q=payload([100]*14+[139]*14,28,"r2")
        for row in q["days"][14:]: row["revision"]=2
        self.service.evaluate(q)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0],42)

    def test_series_change_ends_episode(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        result=self.service.evaluate(payload([100]*14+[140]*14+[140]*7,35,"r2",series="s2"))
        self.assertEqual(result["status"],"SERIES_CHANGED")

    def test_cooldown_and_expiry_are_not_resolution(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        result=self.service.evaluate(payload([100]*14+[140]*70,84,"r2"))
        self.assertEqual(result["status"],"EXPIRED")
        result=self.service.evaluate(payload([100]*14+[140]*70+[180]*7,91,"r3"))
        self.assertEqual(result["status"],"COOLDOWN")

    def test_out_of_order_is_rejected(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        with self.assertRaises(MessageConflict): self.service.evaluate(payload([100]*21,21,"r2"))

    def test_context_and_shared_phone_require_explicit_values(self):
        for flag in ("shared_phone","context_declared"):
            p=payload([100]*14+[140]*14,request=flag,profile=flag); p[flag]=True
            self.assertEqual(self.service.evaluate(p)["status"],"CONTEXT_REVIEW")
        p=payload([100]*28); p["assignment_verified"]=False
        self.assertEqual(self.service.evaluate(p)["status"],"CONTEXT_REVIEW")
        p["shared_phone"]=None
        with self.assertRaises(ValueError): parse_payload(p)

    def test_from_zero_absolute_comparison_without_percent(self):
        result=self.service.evaluate(payload([0]*14+[30]*14))
        self.assertEqual(result["status"],"ACTIVE")
        self.assertIsNone(result["card"]["statistics"]["percent_change"])

    def test_fraction_boundary_not_rounded(self):
        p=payload([100]*14+[120]*14)
        s=statistics(p["days"][14:],p["days"][:14])
        self.assertEqual(s["minimum"],Q(20))
        self.assertEqual(direction(s),"INCREASE")
        p["days"][-1]["minutes"]=119.99
        self.assertIsNone(direction(statistics(p["days"][14:],p["days"][:14])))

    def test_duplicate_concurrent_requests_create_once(self):
        p=payload([100]*14+[140]*14)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(self.service.evaluate,[p]*4))
        self.assertEqual(sum(not r["replayed"] for r in results),1)
        self.assertEqual(len(self.service.history("p1")),1)

    def test_only_new_days_needed_after_opening(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        p=payload([100]*14+[140]*14+[100]*14,42,"r2"); p["days"]=p["days"][28:]
        self.assertEqual(self.service.evaluate(p)["status"],"RESOLVED")

    def test_shared_cap_counts_created_even_when_withdrawn(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        corrected=payload([100]*28,28,"r2")
        for row in corrected["days"][14:]: row["revision"]=2
        self.service.evaluate(corrected)
        p=payload([100]*28+[140]*14,42,"r3")
        for row in p["days"][14:28]: row["revision"]=2
        self.assertEqual(self.service.evaluate(p)["status"],"CARD_LIMIT")

    def test_new_card_allowed_after_cap_and_cooldown(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        self.service.evaluate(payload([100]*14+[140]*14+[100]*14,42,"r2"))
        p=payload([100]*14+[140]*14+[100]*14+[150]*14,56,"r3")
        self.assertEqual(self.service.evaluate(p)["action"],"CREATE")

    def test_health_failure_when_store_removed(self):
        settings=Settings(token=TOKEN,adult_messages_enabled=True,adult_messages_repository_path=self.path)
        with TestClient(create_app(settings)) as c:
            self.assertEqual(c.get("/health").status_code,200)
            self.path.unlink()
            self.assertEqual(c.get("/health").status_code,503)
            self.assertEqual(c.post("/v1/adult-messages/evaluate",json=payload([100]*28),headers=HEADERS).status_code,503)
            self.assertFalse(self.path.exists())

    def test_dst_day_duration_limits(self):
        # Domingo 8/3/2026 en New York tiene 23 horas.
        p=payload([100]*28)
        p["time_zone"]="America/New_York"; p["evaluation_date"]="2026-03-09"
        p["days"]=[{"date":"2026-03-08","revision":1,"minutes":1381,"observed":True,"quality_verified":True}]
        with self.assertRaises(ValueError): parse_payload(p)
        p["days"][0]["minutes"]=1380
        self.assertEqual(parse_payload(p)["days"][0]["minutes"],1380)

    def test_invalid_inputs(self):
        base=payload([100]*28)
        cases=[]
        for field,value in (("minutes",True),("minutes",float("nan")),("minutes",1441),("revision",True)):
            p=deepcopy(base); p["days"][0][field]=value; cases.append(p)
        p=deepcopy(base); p["days"].append(p["days"][0]); cases.append(p)
        p=deepcopy(base); p["pmum_score"]=4; cases.append(p)
        p=deepcopy(base); p["evaluation_date"]=(START+timedelta(days=29)).isoformat(); cases.append(p)
        for p in cases:
            with self.subTest(p=p), self.assertRaises(ValueError): parse_payload(p)

    def test_http_auth_disabled_and_roundtrip(self):
        settings=Settings(token=TOKEN,adult_messages_enabled=True,adult_messages_repository_path=self.path)
        with TestClient(create_app(settings)) as c:
            self.assertEqual(c.post("/v1/adult-messages/evaluate",json=payload([100]*28)).status_code,401)
            r=c.post("/v1/adult-messages/evaluate",json=payload([100]*14+[140]*14),headers=HEADERS)
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()["status"],"ACTIVE")
            h=c.get("/v1/adult-messages/profiles/p1/history",headers=HEADERS)
            self.assertEqual(len(h.json()["versions"]),1)
        with TestClient(create_app(Settings(token=TOKEN))) as c:
            self.assertEqual(c.post("/v1/adult-messages/evaluate",json={},headers=HEADERS).status_code,503)


if __name__ == "__main__":
    unittest.main()
