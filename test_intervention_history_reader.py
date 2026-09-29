"""Regression tests for evidence of offered child activities."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from intervention_history import (
    append_intervention_offer,
    append_intervention_record,
    create_intervention_offer,
    create_intervention_record,
    SOURCE_CHILD_INITIATED,
)
from intervention_history_reader import read_linked_offer_responses
from recommendations import CONTEXT_VOLUNTARY


class OfferHistoryReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "interventions.jsonl"
        self.offer = {
            "event_type": "offer",
            "offer_id": "offer-1",
            "child_id": 3,
            "source": "child_initiated",
            "context": "voluntary",
            "activities_offered": ["drawing", "reading", "ball"],
        }
        self.response = {
            **self.offer,
            "event_type": "response",
            "response": "selected",
            "selected_activity_id": "reading",
            "intervention_id": "response-1",
        }

    def write(self, *events):
        self.path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

    def test_valid_pair_preserves_exposure_and_selection(self):
        self.write(self.offer, self.response)
        (pair,) = read_linked_offer_responses(self.path)
        self.assertEqual(pair.child_id, 3)
        self.assertEqual(pair.activities_offered, ("drawing", "reading", "ball"))
        self.assertEqual(pair.selected_activity_id, "reading")

    def test_records_written_by_existing_api_are_readable(self):
        offer = create_intervention_offer(
            child_id=3,
            source=SOURCE_CHILD_INITIATED,
            context=CONTEXT_VOLUNTARY,
            activities_offered=("creative_story_01", "movement_ball_01"),
        )
        response = create_intervention_record(
            child_id=3,
            source=offer.source,
            context=offer.context,
            activities_offered=offer.activities_offered,
            response="selected",
            selected_activity_id="movement_ball_01",
            offer_id=offer.offer_id,
        )
        append_intervention_offer(offer, output_path=str(self.path))
        append_intervention_record(response, output_path=str(self.path))
        (pair,) = read_linked_offer_responses(self.path)
        self.assertEqual(pair.offer_id, offer.offer_id)
        self.assertEqual(pair.selected_activity_id, "movement_ball_01")

    def test_legacy_and_unlinked_responses_do_not_count(self):
        legacy = {key: value for key, value in self.response.items()
                  if key not in ("offer_id", "event_type")}
        unlinked = {**self.response, "offer_id": None}
        self.write(legacy, unlinked, self.offer)
        self.assertEqual(read_linked_offer_responses(self.path), ())

    def test_missing_prior_offer_is_an_error(self):
        self.write(self.response)
        with self.assertRaisesRegex(ValueError, "missing prior offer"):
            read_linked_offer_responses(self.path)

    def test_mismatched_child_or_activities_is_an_error(self):
        for change in ({"child_id": 4}, {"activities_offered": ["reading"]}):
            with self.subTest(change=change):
                self.write(self.offer, {**self.response, **change})
                with self.assertRaisesRegex(ValueError, "differs from offer"):
                    read_linked_offer_responses(self.path)

    def test_selection_must_have_been_offered(self):
        self.write(self.offer, {**self.response, "selected_activity_id": "other"})
        with self.assertRaisesRegex(ValueError, "selection was not offered"):
            read_linked_offer_responses(self.path)

    def test_second_response_for_offer_is_an_error(self):
        self.write(self.offer, self.response, {**self.response, "intervention_id": "response-2"})
        with self.assertRaisesRegex(ValueError, "duplicate response"):
            read_linked_offer_responses(self.path)

    def test_invalid_json_is_an_error(self):
        self.path.write_text("{\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Line 1: invalid JSON"):
            read_linked_offer_responses(self.path)

    def test_explicit_null_event_type_is_not_legacy(self):
        self.write({**self.response, "event_type": None})
        with self.assertRaisesRegex(ValueError, "unknown event_type"):
            read_linked_offer_responses(self.path)


if __name__ == "__main__":
    unittest.main()
