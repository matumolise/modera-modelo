"""Regresiones de escritura de ofertas ficticias; no prueban pantalla Android."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from intervention_engine import request_voluntary_intervention
from intervention_history import append_intervention_offer, append_intervention_record
from intervention_history_reader import read_linked_offer_responses
from intervention_service import create_offer_from_decision, register_offer_response


class ChildOfferClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"fixture.jsonl"
        self.time=datetime(2026,1,1,12,tzinfo=timezone.utc)
        self.offer=create_offer_from_decision(1,request_voluntary_intervention(random_seed=42),timestamp=self.time,persist=False)
        self.record=register_offer_response(self.offer,"selected",self.offer.activities_offered[0],timestamp=self.time+timedelta(minutes=1),persist=False)

    def seed(self):
        append_intervention_offer(self.offer,str(self.path))

    def test_retries_preserve_one_offer_and_response(self):
        self.seed(); append_intervention_record(self.record,str(self.path)); original=self.path.read_bytes()
        append_intervention_offer(self.offer,str(self.path))
        append_intervention_record(self.record,str(self.path))
        self.assertEqual(self.path.read_bytes(),original)
        self.assertEqual(len(read_linked_offer_responses(self.path)),1)

    def test_missing_offer_rejected_before_write(self):
        with self.assertRaises(ValueError):append_intervention_record(self.record,str(self.path))
        self.assertFalse(self.path.exists())

    def test_second_response_rejected_without_poisoning_stream(self):
        self.seed(); append_intervention_record(self.record,str(self.path)); original=self.path.read_bytes()
        with self.assertRaises(ValueError):append_intervention_record(replace(self.record,intervention_id="fictitious-second"),str(self.path))
        self.assertEqual(self.path.read_bytes(),original)

    def test_same_offer_id_changed_content_rejected(self):
        self.seed(); original=self.path.read_bytes()
        with self.assertRaises(ValueError):append_intervention_offer(replace(self.offer,child_id=2),str(self.path))
        self.assertEqual(self.path.read_bytes(),original)

    def test_response_before_offer_rejected(self):
        with self.assertRaises(ValueError):register_offer_response(self.offer,"ignored",timestamp=self.time-timedelta(seconds=1),persist=False)

    def test_boolean_child_id_rejected(self):
        with self.assertRaises(ValueError):create_offer_from_decision(True,request_voluntary_intervention(random_seed=42),persist=False)

    def test_replace_failure_leaves_original_bytes(self):
        self.seed(); original=self.path.read_bytes()
        with patch("os.replace",side_effect=OSError("fictitious interruption")):
            with self.assertRaises(OSError):append_intervention_record(self.record,str(self.path))
        self.assertEqual(self.path.read_bytes(),original)
        self.assertEqual(len(list(self.path.parent.glob("*.tmp"))),0)

    def test_concurrent_retries_commit_one_event(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _:append_intervention_offer(self.offer,str(self.path)),range(8)))
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()),1)

    def test_new_process_retry_keeps_original(self):
        self.seed(); append_intervention_record(self.record,str(self.path)); original=self.path.read_bytes()
        # Nuevo intérprete; reenvío del evento congelado, no creación de otro UUID.
        code="from pathlib import Path; import json,sys; from intervention_history import _append_jsonl; p=Path(sys.argv[1]); [_append_jsonl(json.loads(line),str(p)) for line in p.read_text(encoding='utf-8').splitlines()]"
        subprocess.run([sys.executable,"-c",code,str(self.path)],check=True,capture_output=True)
        self.assertEqual(self.path.read_bytes(),original)

    def test_unknown_delivery_does_not_become_rejection(self):
        self.seed()
        self.assertEqual(read_linked_offer_responses(self.path),())


if __name__=="__main__":unittest.main()
