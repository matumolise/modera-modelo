"""Regresiones de contradicciones demostradas y preservación de historia/replay."""
from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from analytics_service.adult_messages import AdultMessageService, MessageConflict, MessageUnavailable, CONFIG_FINGERPRINT
from tests.test_adult_messages import payload, START


class BoundedAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name)/"messages.sqlite3"
        self.service = AdultMessageService(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return {table: db.execute("SELECT * FROM "+table+" ORDER BY rowid").fetchall()
                    for table in ("config","states","receipts","evaluations","revisions","cards")}

    def correction(self, day=28, request="correct"):
        p=payload([100]*day,day,request)
        for row in p["days"][14:28]: row["revision"]=2
        return p

    def test_zone_reuse_without_episode_conflicts_without_writes(self):
        self.service.evaluate(payload([100]*28))
        before=self.snapshot()
        p=payload([100]*28+[140]*14,42,"changed-zone")
        p["time_zone"]="America/New_York"
        with self.assertRaisesRegex(MessageConflict,"series_time_zone_conflict"):
            self.service.evaluate(p)
        self.assertEqual(self.snapshot(),before)

    def test_zone_reuse_with_active_episode_also_conflicts(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        p=payload([100]*14+[140]*21,35,"changed-zone")
        p["time_zone"]="America/New_York"
        before=self.snapshot()
        with self.assertRaises(MessageConflict): self.service.evaluate(p)
        self.assertEqual(self.snapshot(),before)

    def test_new_series_allows_zone_change_and_ends_old_episode(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        p=payload([100]*14+[140]*21,35,"changed-series",series="s2")
        p["time_zone"]="America/New_York"
        result=self.service.evaluate(p)
        self.assertEqual(result["status"],"SERIES_CHANGED")

    def test_restart_does_not_recreate_lost_cards(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        with closing(sqlite3.connect(self.path)) as db, db: db.execute("DROP TABLE cards")
        original=self.path.read_bytes()
        with self.assertRaises(MessageUnavailable): AdultMessageService(self.path)
        self.assertEqual(self.path.read_bytes(),original)
        self.assertFalse(self.service.check_ready())
        with closing(sqlite3.connect(self.path)) as db, db:
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("cards",names)

    def test_empty_existing_file_is_not_silently_initialized(self):
        other=self.path.with_name("empty.sqlite3"); other.touch()
        with self.assertRaises(MessageUnavailable): AdultMessageService(other)
        self.assertEqual(other.stat().st_size,0)

    def test_configuration_conflict_still_explicit(self):
        with closing(sqlite3.connect(self.path)) as db, db: db.execute("UPDATE config SET fingerprint='wrong'")
        with self.assertRaisesRegex(MessageConflict,"configuration_changed_requires_new_store"):
            AdultMessageService(self.path)

    def test_c1_warning_does_not_leak_to_new_series_and_old_warning_survives(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        corrected=self.service.evaluate(self.correction())
        expected=corrected["c1_correction_warning_since"]
        self.assertIsNotNone(expected)
        p=payload([100]*35,35,"new-series",series="s2")
        self.assertIsNone(self.service.evaluate(p)["c1_correction_warning_since"])
        self.service=AdultMessageService(self.path)
        p=self.correction(day=42,request="back-to-original")
        self.assertEqual(self.service.evaluate(p)["c1_correction_warning_since"],expected)

    def test_legacy_scalar_warning_migrates_from_original_receipts(self):
        original=payload([100]*14+[140]*14)
        self.service.evaluate(original)
        correction=self.service.evaluate(self.correction())
        # Reproducir la estructura privada del estado v1, conservando recibos.
        with closing(sqlite3.connect(self.path)) as db, db:
            state=json.loads(db.execute("SELECT state FROM states WHERE profile='p1'").fetchone()[0])
            state.pop("c1_stale_by_series", None)
            state["c1_stale_since"]=correction["c1_correction_warning_since"]
            db.execute("UPDATE states SET state=? WHERE profile='p1'",(json.dumps(state),))
        before_receipts=self.snapshot()["receipts"]
        self.service=AdultMessageService(self.path)
        p=payload([100]*35,35,"legacy-new-series",series="s2")
        self.assertIsNone(self.service.evaluate(p)["c1_correction_warning_since"])
        self.assertEqual(self.snapshot()["receipts"][:len(before_receipts)],before_receipts)
        p=self.correction(day=42,request="legacy-old-series")
        self.assertEqual(self.service.evaluate(p)["c1_correction_warning_since"],correction["c1_correction_warning_since"])

    def test_original_replay_after_correction_restart_is_read_only(self):
        original=payload([100]*14+[140]*14)
        receipt=self.service.evaluate(original)
        self.service.evaluate(self.correction())
        self.service.evaluate(self.correction(day=42,request="later"))
        self.service=AdultMessageService(self.path)
        before=self.snapshot()
        replay=self.service.evaluate(original)
        self.assertEqual({k:v for k,v in replay.items() if k!="replayed"},
                         {k:v for k,v in receipt.items() if k!="replayed"})
        self.assertTrue(replay["replayed"])
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.service.history("p1")[-1]["card"]["status"],"WITHDRAWN")

    def test_alias_replay_only_adds_alias_not_new_state_or_version(self):
        original=payload([100]*14+[140]*14)
        receipt=self.service.evaluate(original)
        self.service.evaluate(self.correction())
        before=self.snapshot()
        alias=deepcopy(original); alias["request_id"]="alias-after-correction"
        result=self.service.evaluate(alias)
        after=self.snapshot()
        self.assertTrue(result["replayed"])
        self.assertEqual(result["card"],receipt["card"])
        for table in before:
            if table!="receipts": self.assertEqual(after[table],before[table])
        self.assertEqual(len(after["receipts"]),len(before["receipts"])+1)

    def test_failed_card_write_rolls_back_revisions_state_and_receipt(self):
        self.service.evaluate(payload([100]*28))
        before=self.snapshot()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_card BEFORE INSERT ON cards BEGIN SELECT RAISE(ABORT,'fixture write failure'); END")
        p=payload([100]*28+[140]*14,42,"try-create")
        with self.assertRaises(MessageUnavailable): self.service.evaluate(p)
        self.assertEqual(self.snapshot(),before)
        with closing(sqlite3.connect(self.path)) as db, db: db.execute("DROP TRIGGER reject_card")
        result=self.service.evaluate(p)
        self.assertFalse(result["replayed"])
        self.assertEqual(result["action"],"CREATE")

    def test_shared_limits_and_frozen_dates_preserved_across_corrections(self):
        self.service.evaluate(payload([100]*14+[140]*14))
        q=payload([100]*14+[139]*14,28,"valid-correction")
        for row in q["days"][14:]: row["revision"]=2
        result=self.service.evaluate(q)
        self.assertEqual(result["status"],"ACTIVE")
        self.assertEqual(result["card"]["opening_reference_start"],START.isoformat())
        with closing(sqlite3.connect(self.path)) as db, db:
            state=json.loads(db.execute("SELECT state FROM states WHERE profile='p1'").fetchone()[0])
        self.assertEqual(len(state["created"]),1)
        self.assertEqual(result["card"]["configuration_fingerprint"],CONFIG_FINGERPRINT)


if __name__=="__main__": unittest.main()
