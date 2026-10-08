"""Vectores compartibles con Android para la referencia v3 experimental."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from historical.android_usage import AndroidCollectorRunSummary, RawAndroidUsageEvent
from historical.interactive_duration_v3 import reconstruct_interactive_day_v3


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "interactive_screen_vectors_v3.json"
NAMES = {15: "SCREEN_INTERACTIVE", 16: "SCREEN_NON_INTERACTIVE",
         26: "DEVICE_SHUTDOWN", 27: "DEVICE_STARTUP"}


def _utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _millis(value):
    return round(value.timestamp() * 1000)


class InteractiveDurationV3Vectors(unittest.TestCase):
    def test_shared_vectors(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for vector in payload["vectors"]:
            with self.subTest(vector=vector["id"]):
                start = _utc(vector.get("day_start_utc", payload["default_day_start_utc"]))
                end = _utc(vector.get("day_end_utc", payload["default_day_end_utc"]))
                start_ms = _millis(start)
                events, summaries = [], []
                for query in vector["queries"]:
                    begin = start_ms + query["begin"] * 60000
                    finish = start_ms + query["end"] * 60000
                    collected = _millis(end + timedelta(minutes=5))
                    for minute, code, ordinal in query["events"]:
                        events.append(RawAndroidUsageEvent(
                            schema_version="raw-usage-event-v1",
                            collector_run_id=query["id"],
                            query_begin_epoch_ms=begin,
                            query_end_epoch_ms=finish,
                            collected_at_epoch_ms=collected,
                            event_time_epoch_ms=start_ms + minute * 60000,
                            event_type_code=code,
                            event_type_name=NAMES[code],
                            query_ordinal=ordinal,
                        ))
                    summaries.append(AndroidCollectorRunSummary(
                        collector_run_id=query["id"],
                        requested_begin_epoch_ms=begin,
                        requested_end_epoch_ms=finish,
                        collected_at_epoch_ms=collected,
                        usage_access_available=query["success"],
                        query_returned_null=False,
                        event_count=len(query["events"]),
                        error_code=None if query["success"] else "QUERY_FAILED",
                        error_message=None,
                    ))
                result = reconstruct_interactive_day_v3(
                    interval_start=start, interval_end=end,
                    raw_events=events, summaries=summaries,
                )
                self.assertEqual(result.status.value, vector["expected"]["status"])
                self.assertEqual(result.minutes, vector["expected"]["minutes"])
                self.assertEqual(result.missing_reason, vector["expected"]["reason"])

    def test_raw_event_counts_cannot_silently_disagree(self):
        start = datetime(2026, 10, 5, tzinfo=timezone.utc)
        begin, end = _millis(start), _millis(start + timedelta(days=1))
        summary = AndroidCollectorRunSummary(
            collector_run_id="q", requested_begin_epoch_ms=begin,
            requested_end_epoch_ms=end, collected_at_epoch_ms=end,
            usage_access_available=True, query_returned_null=False,
            event_count=1, error_code=None, error_message=None,
        )
        with self.assertRaisesRegex(ValueError, "event_count"):
            reconstruct_interactive_day_v3(
                interval_start=start, interval_end=start + timedelta(days=1),
                raw_events=[], summaries=[summary],
            )


if __name__ == "__main__":
    unittest.main()
