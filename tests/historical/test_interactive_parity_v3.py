"""El comparador debe fallar ante divergencias reales o export incompleto."""

import json
import unittest
from pathlib import Path

from tools.f12.compare_interactive_v3 import SCHEMA, compare_results


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/interactive_screen_vectors_v3.json"


class InteractiveParityV3Tests(unittest.TestCase):
    def setUp(self):
        self.vectors = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.submission = {"schema_version": SCHEMA, "results": [
            {"id": row["id"], **row["expected"]}
            for row in self.vectors["vectors"]
        ]}

    def test_all_cases_match(self):
        self.assertEqual(compare_results(self.vectors, self.submission), [])

    def test_rejects_missing_duplicate_and_unknown_cases(self):
        changed = {**self.submission, "results": self.submission["results"][1:]
                   + [self.submission["results"][1],
                      {"id": "extra", "status": "MISSING", "minutes": None,
                       "reason": "UNKNOWN"}]}
        errors = compare_results(self.vectors, changed)
        self.assertTrue(any("caso faltante" in error for error in errors))
        self.assertTrue(any("duplicado" in error for error in errors))
        self.assertTrue(any("desconocido" in error for error in errors))

    def test_rejects_wrong_reason_status_and_nonfinite_minutes(self):
        rows = [dict(row) for row in self.submission["results"]]
        rows[0]["status"] = "OBSERVED_ZERO"
        rows[0]["minutes"] = float("nan")
        rows[0]["reason"] = "other"
        errors = compare_results(self.vectors, {**self.submission, "results": rows})
        self.assertEqual(len(errors), 3)

    def test_missing_null_fields_are_not_silently_accepted(self):
        rows = [dict(row) for row in self.submission["results"]]
        missing_index = next(i for i, row in enumerate(rows) if row["status"] == "MISSING")
        del rows[missing_index]["minutes"]
        self.assertTrue(any("campos faltantes" in error for error in
                            compare_results(self.vectors, {**self.submission, "results": rows})))


if __name__ == "__main__":
    unittest.main()
