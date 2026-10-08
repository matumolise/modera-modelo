"""Compara salidas Kotlin de vectores v3 con la referencia Python.

Uso: python tools/f12/compare_interactive_v3.py android-results.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys


FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/interactive_screen_vectors_v3.json"
SCHEMA = "interactive-screen-parity-v3-draft"


def compare_results(vectors: dict, submission: dict) -> list[str]:
    if not isinstance(submission, dict) or submission.get("schema_version") != SCHEMA:
        return ["schema_version incompatible"]
    expected = {v["id"]: v["expected"] for v in vectors["vectors"]}
    rows = submission.get("results")
    if not isinstance(rows, list):
        return ["results debe ser una lista"]
    actual: dict[str, dict] = {}
    errors: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            errors.append("resultado sin id válido")
            continue
        case_id = row["id"]
        if case_id in actual:
            errors.append(f"{case_id}: id duplicado")
        actual[case_id] = row
    for case_id in sorted(expected.keys() - actual.keys()):
        errors.append(f"{case_id}: caso faltante")
    for case_id in sorted(actual.keys() - expected.keys()):
        errors.append(f"{case_id}: caso desconocido")
    for case_id in sorted(actual.keys() & expected.keys()):
        row, reference = actual[case_id], expected[case_id]
        missing_fields = {"status", "minutes", "reason"} - row.keys()
        if missing_fields:
            errors.append(f"{case_id}: campos faltantes {sorted(missing_fields)}")
            continue
        if row.get("status") != reference["status"]:
            errors.append(f"{case_id}: status {row.get('status')!r} != {reference['status']!r}")
        if row.get("reason") != reference["reason"]:
            errors.append(f"{case_id}: reason {row.get('reason')!r} != {reference['reason']!r}")
        value, expected_value = row.get("minutes"), reference["minutes"]
        if expected_value is None:
            if value is not None:
                errors.append(f"{case_id}: minutes debe ser null")
        elif (type(value) not in (float, int) or not math.isfinite(value)
              or abs(value - expected_value) > 1e-6):
            errors.append(f"{case_id}: minutes {value!r} != {expected_value!r}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python tools/f12/compare_interactive_v3.py android-results.json")
        return 2
    try:
        vectors = json.loads(FIXTURE.read_text(encoding="utf-8"))
        submission = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        errors = compare_results(vectors, submission)
    except (OSError, ValueError) as exc:
        print(f"Error al leer JSON: {exc}")
        return 2
    for error in errors:
        print(error)
    if errors:
        print(f"FAIL: {len(errors)} diferencias")
        return 1
    print(f"PASS: {len(vectors['vectors'])} casos coinciden en estado, minutos y motivo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
