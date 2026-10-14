"""Controlled fictional offers; no physical phone, family or delivery validation."""
import argparse
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analytics_service.child_offers import ChildOfferCoordinator, OfferEvidence, POLICY

BASE = datetime.fromisoformat("2026-01-01T10:00:00-03:00")


def fixture(at, interval, **changes):
    return replace(OfferEvidence(
        profile_id="fictitious-child", series_id="fictitious-series", interval_id=interval,
        now=at.isoformat(), interval_started_at=(at - timedelta(hours=1)).isoformat(),
        bedtime_at=at.replace(hour=21, minute=0, second=0).isoformat(),
        automatic_enabled=True, assignment_verified=True, shared_phone=False,
        capture_verified=True, screen_interactive=True, game_active=False,
        in_school_period=False, eligibility_state="known", eligibility={},
    ), **changes)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def event(service, request, offer, at, kind, **extra):
    return service.record_event(request, profile_id=offer["profile_id"], offer_id=offer["offer_id"],
        event=kind, occurred_at=at.isoformat(), now=at.isoformat(), **extra)


def run(root):
    cases = {}
    path = root / "channels.sqlite"
    service = ChildOfferCoordinator(path, create=True)
    initial = fixture(BASE, "continuous-1", game_active=True)
    first = service.evaluate("first", initial)
    event(service, "notification", first["offer"], BASE, "delivered", channel="notification")
    later = BASE + timedelta(minutes=1)
    overlay = service.evaluate("exit-game", fixture(later, "continuous-1",
        interval_started_at=initial.interval_started_at))
    require(overlay["offer"]["offer_id"] == first["offer"]["offer_id"], "Channel duplicated offer")
    event(service, "overlay", first["offer"], later, "delivered", channel="overlay")
    response = event(service, "selected", first["offer"], later, "selected",
        selected_activity_id=first["offer"]["activities_offered"][0])
    service = ChildOfferCoordinator(path)
    replay = service.evaluate("first", initial)
    require(replay == {**first, "replayed": True}, "Original receipt changed")
    cases["notification_overlay_restart"] = {"initial": first, "overlay": overlay,
        "response": response, "replay": replay, "history": service.history("fictitious-child")}

    service = ChildOfferCoordinator(root / "bedtime.sqlite", create=True)
    at = BASE.replace(hour=20, minute=30)
    bed = service.evaluate("bed", fixture(at, "bed-interval"))
    require(bed["offer"]["context"] == "bedtime", "Missing bedtime priority")
    event(service, "bed-delivery", bed["offer"], at, "delivered", channel="overlay")
    event(service, "bed-postponed", bed["offer"], at, "postponed")
    cases["bedtime"] = service.history("fictitious-child")

    service = ChildOfferCoordinator(root / "rejections.sqlite", create=True)
    for index in range(2):
        at = BASE + timedelta(hours=index * 2)
        result = service.evaluate("eval-" + str(index), fixture(at, "interval-" + str(index)))
        event(service, "delivery-" + str(index), result["offer"], at, "delivered", channel="overlay")
        event(service, "reject-" + str(index), result["offer"], at, "rejected")
    pause = service.evaluate("pause", fixture(BASE + timedelta(hours=3), "next"))
    require(pause["reason"] == "rejection_pause", "Missing rejection pause")
    cases["rejections"] = {"result": pause, "history": service.history("fictitious-child")}

    service = ChildOfferCoordinator(root / "unknown.sqlite", create=True)
    first = service.evaluate("first", fixture(BASE, "interval-1"))
    at = BASE + timedelta(minutes=20)
    unknown = service.evaluate("expiry", fixture(at, "interval-2"))
    require(unknown["reason"] == "delivery_reconciliation_required", "Unknown delivery was fabricated")
    failed = event(service, "failed", first["offer"], at, "delivery_failed")
    recovered = service.evaluate("retry-new-interval", fixture(at, "interval-2"))
    require(recovered["status"] == "offer", "Explicit failure did not release reservation")
    cases["unknown_delivery"] = {"unknown": unknown, "failed": failed,
        "recovered": recovered, "history": service.history("fictitious-child")}

    service = ChildOfferCoordinator(root / "insufficient.sqlite", create=True)
    insufficient = service.evaluate("insufficient", fixture(BASE, "interval-1", capture_verified=False))
    require(insufficient["reason"] == "capture_unverified", "Unknown coverage promoted")
    cases["insufficient_evidence"] = {"result": insufficient, "history": service.history("fictitious-child")}
    return {"status": "PASS", "evidence": "FICTITIOUS_CONTROLLED_FIXTURE",
        "scope": "coordinator_contract_not_real_capture_delivery_or_effectiveness",
        "fixture_quality_basis": "Explicit constructed identity, continuous interval, clock and coverage; no inference from successful preparation",
        "policy": POLICY, "cases": cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        report = run(Path(directory))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("PASS: 5 controlled fictitious cases; coordination, receipt replay and delivery reconciliation. No physical validation.")


if __name__ == "__main__":
    main()
