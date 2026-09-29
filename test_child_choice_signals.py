"""Tests for bounded choice signals in the existing child selector."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from child_choice_signals import selected_activity_counts
from intervention_engine import request_voluntary_intervention
from intervention_history import (
    SOURCE_CHILD_INITIATED,
    append_intervention_offer,
    append_intervention_record,
    create_intervention_offer,
    create_intervention_record,
)
from intervention_history_reader import LinkedOfferResponse, read_linked_offer_responses
from recommendations import (
    ActivityEligibility,
    CONTEXT_BEDTIME,
    CONTEXT_VOLUNTARY,
    recommend_activities,
)


class ChildChoiceSignalTests(unittest.TestCase):
    def interaction(self, child_id=1, context=CONTEXT_VOLUNTARY,
                    response="selected", selected="creative_story_01"):
        return LinkedOfferResponse(
            offer_id="offer-1",
            child_id=child_id,
            source="child_initiated",
            context=context,
            activities_offered=("creative_story_01", "creative_animal_01"),
            response=response,
            selected_activity_id=selected,
        )

    def test_only_linked_choices_of_same_child_and_context_count(self):
        records = [
            self.interaction(),
            self.interaction(),
            self.interaction(child_id=2),
            self.interaction(context=CONTEXT_BEDTIME),
            self.interaction(response="rejected", selected=None),
        ]
        self.assertEqual(
            selected_activity_counts(records, child_id=1, context=CONTEXT_VOLUNTARY),
            {"creative_story_01": 2},
        )

    def test_persisted_choices_can_feed_selector(self):
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "history.jsonl")
            for _ in range(3):
                offer = create_intervention_offer(
                    child_id=1,
                    source=SOURCE_CHILD_INITIATED,
                    context=CONTEXT_VOLUNTARY,
                    activities_offered=("creative_story_01", "creative_animal_01"),
                )
                record = create_intervention_record(
                    child_id=1,
                    source=offer.source,
                    context=offer.context,
                    activities_offered=offer.activities_offered,
                    response="selected",
                    selected_activity_id="creative_story_01",
                    offer_id=offer.offer_id,
                )
                append_intervention_offer(offer, output_path=path)
                append_intervention_record(record, output_path=path)
            counts = selected_activity_counts(
                read_linked_offer_responses(path), 1, CONTEXT_VOLUNTARY
            )
        self.assertEqual(counts, {"creative_story_01": 3})
        decision = request_voluntary_intervention(
            selected_activity_counts=counts, random_seed=42
        )
        self.assertTrue(decision.should_intervene)

    def test_single_selection_does_not_change_existing_ranking(self):
        baseline = recommend_activities(CONTEXT_VOLUNTARY, random_seed=42)
        one_choice = recommend_activities(
            CONTEXT_VOLUNTARY,
            random_seed=42,
            selected_activity_counts={"creative_story_01": 1},
        )
        self.assertEqual(one_choice, baseline)

    def test_repeated_choices_raise_selection_without_locking_it(self):
        def shown(seed, counts=None):
            return any(
                activity.activity_id == "creative_story_01"
                for activity in recommend_activities(
                    CONTEXT_VOLUNTARY,
                    random_seed=seed,
                    selected_activity_counts=counts,
                )
            )

        baseline = sum(shown(seed) for seed in range(100))
        favored = sum(shown(seed, {"creative_story_01": 10}) for seed in range(100))
        self.assertGreater(favored, baseline)
        self.assertLess(favored, 100)

    def test_eligibility_and_recent_offer_penalty_still_apply(self):
        counts = {"creative_story_01": 1000}
        ineligible = request_voluntary_intervention(
            eligibility=ActivityEligibility(
                excluded_activity_ids=("creative_story_01",),
            ),
            selected_activity_counts=counts,
            random_seed=42,
        )
        self.assertNotIn(
            "creative_story_01",
            {activity.activity_id for activity in ineligible.activities},
        )
        recent = recommend_activities(
            CONTEXT_VOLUNTARY,
            recently_shown_ids=("creative_story_01",),
            selected_activity_counts=counts,
            random_seed=42,
        )
        self.assertNotIn(
            "creative_story_01", {activity.activity_id for activity in recent}
        )

        bedtime = recommend_activities(
            CONTEXT_BEDTIME,
            selected_activity_counts={"movement_ball_01": 1000},
            random_seed=42,
        )
        self.assertNotIn(
            "movement_ball_01", {activity.activity_id for activity in bedtime}
        )
        self.assertTrue(all(activity.bedtime_suitable for activity in bedtime))

    def test_invalid_counts_are_rejected(self):
        for counts in ({"creative_story_01": -1}, {"creative_story_01": 1.5}):
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    recommend_activities(
                        CONTEXT_VOLUNTARY, selected_activity_counts=counts
                    )


if __name__ == "__main__":
    unittest.main()
