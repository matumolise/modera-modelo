"""Recuperación durable, compatibilidad de reintentos y publicación conjunta."""

from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from historical import C1DetectorConfig, Coverage, ObservationStatus
from historical.detector import DetectorEvaluationOutcome
from historical.emitter import DetectionEventDecision
from historical.interpretation import build_historical_interpretation
from historical.persistence import FileHistoricalRepository, HistoricalStreamKey
from historical.service import process_c1_representation
from tests.historical.test_service import representation


class DurableReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "history.json"
        self.repository = FileHistoricalRepository(self.path)
        self.config = C1DetectorConfig(k=0.5, threshold=3.0, min_history=3)
        self.key = HistoricalStreamKey.from_c1(
            "child-001", "daily-use-minutes.v1", self.config, "analysis-v1",
        )

    def process(self, current, **overrides):
        args = dict(
            repository=self.repository, current=current, stream_key=self.key,
            config=self.config, evaluation_id=f"eval-{current.representation_record_id}",
            event_id=f"event-{current.representation_record_id}",
            analysis_version="analysis-v1", emitter_version="emitter-v1",
            computed_at=current.interval_end, emitted_at=current.interval_end,
        )
        args.update(overrides)
        return process_c1_representation(**args)

    def seed(self):
        inputs = [representation(day, value)
                  for day, value in enumerate([60, 70, 80, 75, 150])]
        return inputs, [self.process(current) for current in inputs]

    def test_restart_recovers_all_outcomes_without_reanalysis_or_state_rewind(self):
        inputs, results = self.seed()
        self.assertIs(results[0].evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertIs(results[3].evaluation.outcome, DetectorEvaluationOutcome.NO_CHANGE)
        self.assertIs(results[4].emission.decision, DetectionEventDecision.EMIT)
        self.process(representation(5, 170))
        latest_state = self.repository.load_state(self.key)
        before = self.path.read_bytes()
        self.repository = FileHistoricalRepository(self.path)

        with patch("historical.service.analyze_c1_representation",
                   side_effect=AssertionError("must not reanalyze")), patch.object(
                       self.repository, "_write_document",
                       side_effect=AssertionError("must not rewrite")):
            for current, original in zip(inputs, results):
                recovered = self.process(
                    current, evaluation_id="new-eval", event_id="new-event",
                    computed_at=current.interval_end + timedelta(days=20),
                    emitted_at=current.interval_end + timedelta(days=20),
                )
                self.assertEqual(recovered, original)
                self.assertIs(recovered.evaluation.outcome, original.evaluation.outcome)
                self.assertIs(recovered.emission.decision, original.emission.decision)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.repository.load_state(self.key), latest_state)

        kwargs = dict(
            current=inputs[4], interpretation_id="interpretation-1",
            interpretation_version="interpretation-v1", computed_at=inputs[4].interval_end,
        )
        recovered = self.process(inputs[4])
        self.assertEqual(
            build_historical_interpretation(result=results[4], **kwargs),
            build_historical_interpretation(result=recovered, **kwargs),
        )

    def test_missing_abstention_survives_restart(self):
        current = replace(representation(0, 60), value=None, status=ObservationStatus.MISSING)
        original = self.process(current)
        self.repository = FileHistoricalRepository(self.path)
        recovered = self.process(current)
        self.assertEqual(recovered, original)
        self.assertIs(recovered.evaluation.outcome, DetectorEvaluationOutcome.ABSTAIN)
        self.assertIs(recovered.evaluation.abstention_reason, original.evaluation.abstention_reason)

    def test_incompatible_representation_is_rejected_without_writes(self):
        current = representation(0, 60)
        self.process(current)
        before = self.path.read_bytes()
        changes = [
            {"value": 65}, {"unit": "seconds"}, {"phenomenon": "other"},
            {"coverage": Coverage(value=0.5, basis="test")},
            {"quality_flags": ("OTHER",)},
            {"provenance": replace(current.provenance, input_fingerprint="other")},
            {"interval_end": current.interval_end + timedelta(hours=1)},
        ]
        for fields in changes:
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, "incompatible"):
                self.process(replace(current, **fields))
            self.assertEqual(self.path.read_bytes(), before)

    def test_incompatible_policy_is_rejected_even_without_original_event(self):
        current = representation(0, 60)
        self.assertIsNone(self.process(current).emission.event)
        before = self.path.read_bytes()
        other_config = C1DetectorConfig(k=1.0, threshold=3.0, min_history=3)
        overrides = [
            {"emitter_version": "emitter-v2"},
            {"analysis_version": "analysis-v2",
             "stream_key": replace(self.key, analysis_version="analysis-v2")},
            {"config": other_config,
             "stream_key": HistoricalStreamKey.from_c1(
                 current.subject_id, current.representation_spec_id,
                 other_config, "analysis-v1")},
        ]
        for fields in overrides:
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, "incompatible"):
                self.process(current, **fields)
            self.assertEqual(self.path.read_bytes(), before)

    def test_failure_before_replace_publishes_no_partial_progress(self):
        self.process(representation(0, 60))
        before = self.path.read_bytes()
        current = representation(1, 70)
        with patch("historical.persistence.os.replace", side_effect=OSError("write failed")):
            with self.assertRaises(OSError):
                self.process(current)
        self.assertEqual(self.path.read_bytes(), before)
        self.repository = FileHistoricalRepository(self.path)
        self.assertFalse(self.repository.contains_representation(current.representation_record_id))
        self.assertIsNone(self.repository.load_analysis_result(
            representation=current, stream_key=self.key, emitter_version="emitter-v1"))
        result = self.process(current)
        self.assertEqual(self.repository.load_state(self.key), result.next_state)

    def test_lost_response_after_commit_recovers_original_event(self):
        for day, value in enumerate([60, 70, 80, 75]):
            self.process(representation(day, value))
        current = representation(4, 150)
        save = self.repository.save_analysis_progress
        committed = []

        def lose_response(**kwargs):
            save(**kwargs)
            committed.append(kwargs["result"])
            raise OSError("response lost after commit")

        with patch.object(self.repository, "save_analysis_progress", side_effect=lose_response):
            with self.assertRaises(OSError):
                self.process(current)
        before = self.path.read_bytes()
        self.repository = FileHistoricalRepository(self.path)
        with patch("historical.service.analyze_c1_representation",
                   side_effect=AssertionError("must not reanalyze")):
            recovered = self.process(current, event_id="replacement-id")
        self.assertEqual(recovered, committed[0])
        self.assertIs(recovered.emission.decision, DetectionEventDecision.EMIT)
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_read_does_not_fabricate_receipts_or_rewrite_file(self):
        current = representation(0, 60)
        self.process(current)
        document = json.loads(self.path.read_text())
        document["format_version"] = 1
        del document["receipts"]
        self.path.write_text(json.dumps(document))
        before = self.path.read_bytes()
        self.repository = FileHistoricalRepository(self.path)
        self.assertEqual(len(self.repository.load_history(
            subject_id=current.subject_id,
            representation_spec_id=current.representation_spec_id)), 1)
        with self.assertRaisesRegex(ValueError, "sin recibo recuperable"):
            self.process(current)
        self.assertEqual(self.path.read_bytes(), before)
        self.process(representation(1, 70))
        upgraded = json.loads(self.path.read_text())
        self.assertEqual(upgraded["format_version"], 3)
        self.assertEqual(len(upgraded["representations"]), 2)
        self.assertEqual(set(upgraded["receipts"]), {"service-rep-1"})

    def test_duplicate_repository_save_does_not_rewind_later_state(self):
        inputs, results = self.seed()
        before = self.path.read_bytes()
        added = self.repository.save_analysis_progress(
            representation=inputs[0], stream_key=self.key,
            state=results[0].next_state, result=results[0], emitter_version="emitter-v1",
        )
        self.assertFalse(added)
        self.assertEqual(self.path.read_bytes(), before)

    def test_mismatched_result_is_not_saved(self):
        current = representation(0, 60)
        result = self.process(current)
        before = self.path.read_bytes()
        bad = replace(result, evaluation=replace(result.evaluation,
                                                 representation_record_id="other"))
        with self.assertRaisesRegex(ValueError, "no coincide"):
            self.repository.save_analysis_progress(
                representation=current, stream_key=self.key, state=result.next_state,
                result=bad, emitter_version="emitter-v1",
            )
        self.assertEqual(self.path.read_bytes(), before)

    def test_current_format_without_receipts_is_rejected(self):
        self.process(representation(0, 60))
        document = json.loads(self.path.read_text())
        del document["receipts"]
        self.path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "recibos válidos"):
            self.process(representation(0, 60))

    def test_representation_recomputation_preserves_original_receipt_and_timestamp(self):
        current = representation(0, 60)
        original = self.process(current)
        before = self.path.read_bytes()
        retry = replace(current, computed_at=current.computed_at + timedelta(days=2))
        with patch("historical.service.analyze_c1_representation",
                   side_effect=AssertionError("must not reanalyze")):
            self.assertEqual(self.process(retry), original)
        self.assertEqual(self.path.read_bytes(), before)

    def test_deleted_new_receipt_is_integrity_failure(self):
        current = representation(0, 60)
        self.process(current)
        document = json.loads(self.path.read_text())
        document["receipts"].clear()
        self.path.write_text(json.dumps(document))
        before = self.path.read_bytes()
        with patch("historical.service.analyze_c1_representation",
                   side_effect=AssertionError("must not reanalyze")):
            with self.assertRaisesRegex(ValueError, "integridad"):
                self.process(current)
        self.assertEqual(self.path.read_bytes(), before)

    def test_activation_rejects_low_level_save_without_receipt(self):
        result = self.process(representation(0, 60))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "requiere un recibo"):
            self.repository.save_analysis_progress(
                representation=representation(1, 70), stream_key=self.key,
                state=result.next_state,
            )
        self.assertEqual(self.path.read_bytes(), before)

    def test_pre_activation_record_keeps_explicit_legacy_classification(self):
        current = representation(0, 60)
        self.repository.save_analysis_progress(
            representation=current, stream_key=self.key,
            state=self.repository.load_state(self.key),
        )
        document = json.loads(self.path.read_text())
        self.assertFalse(document["receipts_required"])
        self.assertEqual(document["records_without_receipt"],
                         {current.representation_record_id: "legacy"})
        self.process(representation(1, 70))
        self.assertTrue(json.loads(self.path.read_text())["receipts_required"])
        with self.assertRaisesRegex(ValueError, "legada"):
            self.process(current)

    def test_v2_missing_receipt_is_unclassified_and_never_reanalyzed(self):
        current = representation(0, 60)
        self.process(current)
        document = json.loads(self.path.read_text())
        document["format_version"] = 2
        document["receipts"].clear()
        del document["records_without_receipt"]
        del document["receipts_required"]
        self.path.write_text(json.dumps(document))
        before = self.path.read_bytes()
        with patch("historical.service.analyze_c1_representation",
                   side_effect=AssertionError("must not reanalyze")):
            with self.assertRaisesRegex(ValueError, "no clasificable"):
                self.process(current)
        self.assertEqual(self.path.read_bytes(), before)
        self.process(representation(1, 70))
        upgraded = json.loads(self.path.read_text())
        self.assertEqual(upgraded["format_version"], 3)
        self.assertEqual(upgraded["records_without_receipt"],
                         {current.representation_record_id: "unclassified"})

    def test_intact_v2_receipt_recovers_without_inventing_previous_state(self):
        current = representation(0, 60)
        original = self.process(current)
        document = json.loads(self.path.read_text())
        document["format_version"] = 2
        del document["records_without_receipt"]
        del document["receipts_required"]
        del document["receipts"][current.representation_record_id]["previous_state"]
        self.path.write_text(json.dumps(document))
        before = self.path.read_bytes()
        self.assertEqual(self.process(current), original)
        self.assertEqual(self.path.read_bytes(), before)

    def test_event_receipt_keeps_previous_state_after_later_progress(self):
        from historical.persistence import serialize_analyzer_state
        inputs, results = self.seed()
        expected = serialize_analyzer_state(results[3].next_state)
        event_id = inputs[4].representation_record_id
        self.process(representation(5, 170))
        self.repository = FileHistoricalRepository(self.path)
        self.assertEqual(self.process(inputs[4]), results[4])
        document = json.loads(self.path.read_text())
        self.assertEqual(document["receipts"][event_id]["previous_state"], expected)
