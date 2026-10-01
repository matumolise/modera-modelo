"""The Android exporter sorts by time while retaining original query ordinals."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
from io import StringIO

from tools.f12.audit_usage_events_export import audit


class ExportAuditTests(unittest.TestCase):
    def audit_events(self, events):
        with TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.json"
            exported = Path(directory) / "events.jsonl"
            summary.write_text(json.dumps({
                "collectorRunId": "run-1",
                "requestedBeginEpochMs": 0,
                "requestedEndEpochMs": 1000,
                "eventCount": len(events),
            }), encoding="utf-8")
            exported.write_text(
                "".join(json.dumps({
                    "collectorRunId": "run-1",
                    "queryBeginEpochMs": 0,
                    "queryEndEpochMs": 1000,
                    "eventTimeEpochMs": timestamp,
                    "queryOrdinal": ordinal,
                }) + "\n" for timestamp, ordinal in events),
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                result = audit(summary, exported)
            return result, output.getvalue()

    def test_sorted_export_keeps_original_query_ordinals(self):
        result, output = self.audit_events([(100, 1), (200, 0)])
        self.assertEqual(result, 0, output)

    def test_duplicate_query_ordinal_is_rejected(self):
        result, output = self.audit_events([(100, 0), (200, 0)])
        self.assertEqual(result, 1)
        self.assertIn("duplicate queryOrdinal", output)

    def test_equal_timestamps_must_be_sorted_by_query_ordinal(self):
        result, output = self.audit_events([(100, 1), (100, 0)])
        self.assertEqual(result, 1)
        self.assertIn("not time/ordinal ordered", output)


if __name__ == "__main__":
    unittest.main()
