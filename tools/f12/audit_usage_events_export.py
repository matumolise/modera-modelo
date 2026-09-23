import argparse
import json
import sys
from pathlib import Path


def fail(errors, message):
    errors.append(message)


def audit(summary_path: Path, events_path: Path) -> int:
    errors = []

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"FAIL: cannot read summary: {exc}")
        return 1

    events = []
    try:
        with events_path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    fail(errors, f"invalid JSONL at line {line_number}: {exc}")
    except Exception as exc:
        print(f"FAIL: cannot read events: {exc}")
        return 1

    expected_count = summary.get("eventCount")
    if expected_count != len(events):
        fail(
            errors,
            f"eventCount mismatch: summary={expected_count}, jsonl={len(events)}",
        )

    summary_run_id = summary.get("collectorRunId")
    begin = summary.get("requestedBeginEpochMs")
    end = summary.get("requestedEndEpochMs")

    previous_time = None

    for index, event in enumerate(events):
        if event.get("collectorRunId") != summary_run_id:
            fail(errors, f"event {index}: collectorRunId mismatch")

        if event.get("queryBeginEpochMs") != begin:
            fail(errors, f"event {index}: queryBeginEpochMs mismatch")

        if event.get("queryEndEpochMs") != end:
            fail(errors, f"event {index}: queryEndEpochMs mismatch")

        if event.get("queryOrdinal") != index:
            fail(
                errors,
                f"event {index}: queryOrdinal={event.get('queryOrdinal')} expected={index}",
            )

        event_time = event.get("eventTimeEpochMs")

        if not isinstance(event_time, int):
            fail(errors, f"event {index}: invalid eventTimeEpochMs")
            continue

        if isinstance(begin, int) and isinstance(end, int):
            if not (begin <= event_time < end):
                fail(errors, f"event {index}: timestamp outside query window")

        if previous_time is not None and event_time < previous_time:
            fail(errors, f"event {index}: events are not time ordered")

        previous_time = event_time

    print(f"summary : {summary_path}")
    print(f"events  : {events_path}")
    print(f"runId   : {summary_run_id}")
    print(f"events  : {len(events)}")

    if errors:
        print(f"RESULT  : FAIL ({len(errors)} issue(s))")
        for error in errors:
            print(f" - {error}")
        return 1

    print("RESULT  : PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Audit an F12 Android diagnostic UsageEvents export."
    )
    parser.add_argument("summary", type=Path)
    parser.add_argument("events", type=Path)
    args = parser.parse_args()

    sys.exit(audit(args.summary, args.events))


if __name__ == "__main__":
    main()
