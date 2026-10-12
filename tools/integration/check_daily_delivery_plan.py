"""Valida un plan backend propuesto sin persistir payloads ni enviar HTTP."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from analytics_service.daily_delivery import assess_daily_plan
from analytics_service.json_codec import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            data = source.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("Plan excesivo")
        result = assess_daily_plan(strict_json(data))
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2); stream.write("\n")
        print("PASS: plan validado; READY_TO_FREEZE no significa persistido ni enviado.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ImportError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
