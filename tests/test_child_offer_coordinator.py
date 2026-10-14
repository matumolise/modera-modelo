"""Controlled, fictitious evidence. These tests do not validate phone capture."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import json
import subprocess
import sys

import pytest

from analytics_service.activities import select_activities
from analytics_service.child_offers import ChildOfferCoordinator, OfferEvidence


BASE = datetime.fromisoformat("2026-01-01T10:00:00-03:00")


def evidence(at=BASE, interval="interval-1", **changes):
    return replace(OfferEvidence(
        profile_id="fictitious-family-child", series_id="fictitious-phone-series",
        interval_id=interval, now=at.isoformat(),
        interval_started_at=(at - timedelta(hours=1)).isoformat(),
        bedtime_at=at.replace(hour=21, minute=0, second=0).isoformat(),
        automatic_enabled=True, assignment_verified=True, shared_phone=False,
        capture_verified=True, screen_interactive=True, game_active=False,
        in_school_period=False, eligibility_state="known", eligibility={},
    ), **changes)


@pytest.fixture
def coordinator(tmp_path):
    return ChildOfferCoordinator(tmp_path / "fictitious.sqlite", create=True)


def deliver(coordinator, result, at, request="delivery", channel="overlay"):
    offer = result["offer"]
    return coordinator.record_event(request, profile_id=offer["profile_id"],
        offer_id=offer["offer_id"], event="delivered", occurred_at=at.isoformat(),
        now=at.isoformat(), channel=channel)


def respond(coordinator, result, at, response="postponed", request="response", **extra):
    offer = result["offer"]
    return coordinator.record_event(request, profile_id=offer["profile_id"],
        offer_id=offer["offer_id"], event=response, occurred_at=at.isoformat(),
        now=at.isoformat(), **extra)


def completed(coordinator, at, index, response="postponed"):
    result = coordinator.evaluate("eval-" + str(index), evidence(at, "interval-" + str(index)))
    deliver(coordinator, result, at, "delivery-" + str(index))
    respond(coordinator, result, at, response, "response-" + str(index))
    return result


def test_day_offer_reuses_selector_and_keeps_original_receipts(coordinator):
    data = evidence()
    result = coordinator.evaluate("first", data)
    expected = select_activities({"request_id": "first", "context": "general",
        "interests": [], "eligibility_state": "known", "eligibility": {}, "recently_shown_ids": []})
    assert result["offer"]["selection"] == json.loads(json.dumps(expected))
    assert result["offer"]["delivered_at"] is None
    assert result["offer"]["source"] == "system_daytime"
    deliver(coordinator, result, BASE)
    selected = result["offer"]["activities_offered"][0]
    respond(coordinator, result, BASE, "selected", selected_activity_id=selected)
    replay = coordinator.evaluate("first", data)
    assert replay == {**result, "replayed": True}
    assert coordinator.history(data.profile_id)["offers"][0]["response"] == "selected"
    assert len(coordinator.history(data.profile_id)["offers"]) == 1
    with pytest.raises(ValueError, match="reused"):
        coordinator.evaluate("first", replace(data, game_active=True))


def test_notification_to_overlay_keeps_identity_and_one_delivery(coordinator):
    first = coordinator.evaluate("first", evidence(game_active=True))
    assert first["channel"] == "notification"
    deliver(coordinator, first, BASE, channel="notification")
    later = BASE + timedelta(minutes=1)
    second = coordinator.evaluate("second", evidence(later,
        interval_started_at=evidence().interval_started_at))
    assert second["channel"] == "overlay"
    assert second["offer"]["offer_id"] == first["offer"]["offer_id"]
    ack = deliver(coordinator, second, later, "overlay-ack")
    assert ack["offer"]["delivered_at"] == first["offer"]["created_at"]
    assert ack["offer"]["channels"] == ["notification", "overlay"]


@pytest.mark.parametrize("changes,reason", [
    ({"automatic_enabled": False}, "automatic_disabled"),
    ({"assignment_verified": False}, "identity_uncertain"),
    ({"shared_phone": True}, "identity_uncertain"),
    ({"capture_verified": False}, "capture_unverified"),
    ({"screen_interactive": False}, "screen_inactive"),
    ({"in_school_period": True}, "school_period"),
    ({"eligibility_state": "unknown", "eligibility": None}, "eligibility_unknown"),
])
def test_unknown_conditions_never_generate(coordinator, changes, reason):
    assert coordinator.evaluate("guard", evidence(**changes))["reason"] == reason
    assert not coordinator.history(evidence().profile_id)["offers"]


def test_pending_presentation_rechecks_eligibility_and_identity(coordinator):
    first = coordinator.evaluate("first", evidence())
    assert coordinator.evaluate("identity", evidence(shared_phone=True))["reason"] == "identity_uncertain"
    assert coordinator.evaluate("filter", evidence(eligibility={
        "excluded_activity_ids": first["offer"]["activities_offered"]}))[
            "reason"] == "frozen_offer_no_longer_eligible"
    assert coordinator.evaluate("other-series", evidence(series_id="other"))["reason"] == "outstanding_offer"


def test_bedtime_priority_and_calm_catalog(coordinator):
    at = BASE.replace(hour=19)
    result = coordinator.evaluate("bed", evidence(at, bedtime_at=at.replace(hour=20).isoformat()))
    assert result["offer"]["context"] == "bedtime"
    assert all(a["activity_level"] == "calm" and a["bedtime_suitable"]
               for a in result["offer"]["selection"]["activities"])


@pytest.mark.parametrize("hour,minutes,allowed", [(8, 45, True), (8, 44, False), (7, 60, False), (20, 60, False)])
def test_day_trigger_boundaries(coordinator, hour, minutes, allowed):
    at = BASE.replace(hour=hour)
    result = coordinator.evaluate("boundary", evidence(at,
        bedtime_at=at.replace(hour=23).isoformat(),
        interval_started_at=(at - timedelta(minutes=minutes)).isoformat()))
    assert (result["status"] == "offer") == allowed


def test_shared_cooldown_and_interval_identity(coordinator):
    completed(coordinator, BASE, 1)
    assert coordinator.evaluate("too-soon", evidence(BASE + timedelta(minutes=119), "next"))["reason"] == "shared_cooldown"
    at = BASE + timedelta(minutes=120)
    assert coordinator.evaluate("exact", evidence(at, "next",
        interval_started_at=evidence(BASE + timedelta(minutes=119)).interval_started_at))["status"] == "offer"


def test_consumed_interval_and_changed_start_are_not_new_opportunities(coordinator):
    completed(coordinator, BASE, 1)
    at = BASE + timedelta(hours=3)
    assert coordinator.evaluate("same", evidence(at, interval_started_at=evidence().interval_started_at))["reason"] == "opportunity_consumed"
    with pytest.raises(ValueError, match="original start"):
        coordinator.evaluate("changed", evidence(at))


def test_shared_quota_day_and_bedtime_and_midnight(coordinator):
    completed(coordinator, BASE, 1)
    completed(coordinator, BASE + timedelta(hours=2), 2)
    assert coordinator.evaluate("third-day", evidence(BASE + timedelta(hours=4), "third"))["reason"] == "automatic_quota"
    bed = BASE.replace(hour=20, minute=30)
    completed(coordinator, bed, 3)
    next_morning = BASE + timedelta(days=1) - timedelta(hours=2)
    assert coordinator.evaluate("midnight-reset", evidence(next_morning, "fourth"))["reason"] == "automatic_quota"


def test_bedtime_once_in_rolling_day_even_after_timezone_change(coordinator):
    first_at = BASE.replace(hour=20, minute=30)
    completed(coordinator, first_at, 1)
    later = first_at + timedelta(hours=3)
    assert coordinator.evaluate("second-night", evidence(later, "new",
        bedtime_at=(later + timedelta(minutes=30)).isoformat()))["reason"] == "automatic_quota"


def test_two_rejections_pause_but_postponement_is_not_rejection(coordinator):
    completed(coordinator, BASE, 1, "rejected")
    completed(coordinator, BASE + timedelta(hours=2), 2, "rejected")
    assert coordinator.evaluate("pause", evidence(BASE + timedelta(hours=3), "next"))["reason"] == "rejection_pause"
    at = BASE + timedelta(days=1, hours=2)
    assert coordinator.evaluate("after-pause", evidence(at, "later"))["status"] == "offer"


def test_silence_is_ignored_not_rejection_and_does_not_prove_realization(coordinator):
    first = coordinator.evaluate("first", evidence())
    deliver(coordinator, first, BASE)
    later = BASE + timedelta(hours=2)
    assert coordinator.evaluate("later", evidence(later, "next"))["status"] == "offer"
    offer = coordinator.history(evidence().profile_id)["offers"][0]
    assert offer["status"] == "ignored"
    assert offer["response"] is None
    assert offer["selected_activity_id"] is None


def test_missing_ack_requires_reconciliation_without_fabricating_delivery(coordinator):
    first = coordinator.evaluate("first", evidence())
    at = BASE + timedelta(hours=2)
    assert coordinator.evaluate("later", evidence(at, "next"))["reason"] == "delivery_reconciliation_required"
    assert coordinator.history(evidence().profile_id)["offers"][0]["delivered_at"] is None
    respond(coordinator, first, at, "delivery_failed")
    assert coordinator.evaluate("after-reconciliation", evidence(at, "next"))["status"] == "offer"


def test_late_ack_and_late_response_preserve_actual_times(coordinator):
    first = coordinator.evaluate("first", evidence())
    processing = BASE + timedelta(minutes=20)
    coordinator.evaluate("expiry", evidence(processing, "next"))
    coordinator.record_event("late-ack", profile_id=evidence().profile_id,
        offer_id=first["offer"]["offer_id"], event="delivered", channel="notification",
        occurred_at=BASE.isoformat(), now=processing.isoformat())
    result = coordinator.record_event("late-response", profile_id=evidence().profile_id,
        offer_id=first["offer"]["offer_id"], event="rejected",
        occurred_at=(BASE + timedelta(minutes=1)).isoformat(), now=processing.isoformat())
    assert result["offer"]["status"] == "responded"
    assert result["offer"]["delivered_at"] == first["offer"]["created_at"]
    assert any(e["event"] == "delivery_unknown" for e in coordinator.history(evidence().profile_id)["events"])


def test_invalid_events_do_not_change_state(coordinator):
    first = coordinator.evaluate("first", evidence())
    before = coordinator.history(evidence().profile_id)
    with pytest.raises(ValueError, match="prior confirmed"):
        respond(coordinator, first, BASE, "selected", selected_activity_id=first["offer"]["activities_offered"][0])
    assert coordinator.history(evidence().profile_id) == before
    with pytest.raises(ValueError, match="Expired"):
        deliver(coordinator, first, BASE + timedelta(minutes=10))
    deliver(coordinator, first, BASE)
    with pytest.raises(ValueError, match="not offered"):
        respond(coordinator, first, BASE, "selected", selected_activity_id="not-offered")
    with pytest.raises(ValueError, match="this profile"):
        coordinator.record_event("wrong-profile", profile_id="other-profile", offer_id=first["offer"]["offer_id"],
            event="rejected", occurred_at=BASE.isoformat(), now=BASE.isoformat())


def test_receipts_survive_process_restart_and_concurrent_requests(coordinator):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: coordinator.evaluate("same", evidence()), range(6)))
    assert len({r["offer"]["offer_id"] for r in results}) == 1
    assert sum(not r["replayed"] for r in results) == 1
    code = "from analytics_service.child_offers import *; import json,sys; print(json.dumps(ChildOfferCoordinator(sys.argv[1]).evaluate('same', OfferEvidence(**json.loads(sys.argv[2])))))"
    replay = json.loads(subprocess.check_output([sys.executable, "-c", code, str(coordinator.path), json.dumps(asdict(evidence()))], text=True))
    assert replay == {**next(r for r in results if not r["replayed"]), "replayed": True}
    assert len(coordinator.history(evidence().profile_id)["offers"]) == 1


def test_atomic_rollback_when_receipt_cannot_be_saved(coordinator, monkeypatch):
    import analytics_service.child_offers as module
    original = module._json
    def failed(value):
        if isinstance(value, dict) and value.get("status") == "offer":
            raise OSError("fictitious storage failure")
        return original(value)
    with monkeypatch.context() as patch:
        patch.setattr(module, "_json", failed)
        with pytest.raises(OSError):
            coordinator.evaluate("first", evidence())
    assert not coordinator.history(evidence().profile_id)["offers"]
    assert coordinator.evaluate("first", evidence())["status"] == "offer"


def test_empty_existing_store_and_policy_mismatch_fail_closed(tmp_path, coordinator):
    empty = tmp_path / "incomplete.sqlite"
    empty.touch()
    with pytest.raises(ValueError, match="Incomplete"):
        ChildOfferCoordinator(empty)
    import sqlite3
    with sqlite3.connect(coordinator.path) as db:
        body = json.loads(db.execute("SELECT body FROM state").fetchone()[0])
        body["policy"]["cooldown_minutes"] = 1
        db.execute("UPDATE state SET body=?", (json.dumps(body),))
    with pytest.raises(ValueError, match="mismatch"):
        ChildOfferCoordinator(coordinator.path)


def test_clock_rollback_and_invalid_types_fail_closed(coordinator):
    coordinator.evaluate("first", evidence())
    with pytest.raises(ValueError, match="backwards"):
        coordinator.evaluate("clock", evidence(BASE - timedelta(seconds=1), "other"))
    with pytest.raises(ValueError, match="booleans"):
        coordinator.evaluate("boolean", evidence(capture_verified=1))
    with pytest.raises(ValueError, match="Naive"):
        coordinator.evaluate("naive", evidence(now="2026-01-01T10:00:00"))


def test_profile_isolation_and_empty_eligibility(coordinator):
    coordinator.evaluate("first", evidence())
    assert coordinator.evaluate("other", evidence(profile_id="another-family-child"))["status"] == "offer"
    assert coordinator.evaluate("empty", evidence(profile_id="third-family-child",
        eligibility={"allowed_activity_levels": []}))["reason"] == "no_eligible_activities"


def test_replay_does_not_run_selector_again(coordinator, monkeypatch):
    first = coordinator.evaluate("first", evidence())
    def forbidden(*args, **kwargs):
        raise AssertionError("Replay must not select or generate again")
    monkeypatch.setattr("analytics_service.child_offers.select_activities", forbidden)
    assert coordinator.evaluate("first", evidence()) == {**first, "replayed": True}


def test_lost_store_requires_explicit_initialization(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="missing"):
        ChildOfferCoordinator(path)
    assert not path.exists()


def test_pending_channel_change_requires_first_delivery_confirmation(coordinator):
    first = coordinator.evaluate("first", evidence(game_active=True))
    later = BASE + timedelta(minutes=1)
    changed = evidence(later, interval_started_at=evidence().interval_started_at)
    assert coordinator.evaluate("exit-before-ack", changed)["reason"] == "pending_delivery_confirmation"
    coordinator.record_event("late-delivery", profile_id=first["offer"]["profile_id"],
        offer_id=first["offer"]["offer_id"], event="delivered", channel="notification",
        occurred_at=BASE.isoformat(), now=later.isoformat())
    assert coordinator.evaluate("exit-after-ack", changed)["offer"]["offer_id"] == first["offer"]["offer_id"]


def test_pending_daytime_offer_not_presented_in_bedtime_phase(coordinator):
    at = BASE.replace(hour=19, minute=59)
    first = coordinator.evaluate("first", evidence(at))
    assert first["offer"]["context"] == "general"
    later = at + timedelta(minutes=1)
    assert coordinator.evaluate("phase", evidence(later,
        interval_started_at=evidence(at).interval_started_at))["reason"] == "presentation_context_changed"


def test_repeat_penalty_uses_confirmed_history_not_generation(coordinator):
    first = completed(coordinator, BASE, 1)
    second = coordinator.evaluate("second", evidence(BASE + timedelta(hours=2), "interval-2"))
    expected = select_activities({"request_id": "second", "context": "general", "interests": [],
        "eligibility_state": "known", "eligibility": {},
        "recently_shown_ids": first["offer"]["activities_offered"]})
    assert second["offer"]["selection"] == json.loads(json.dumps(expected))
    assert not set(first["offer"]["activities_offered"]) & set(second["offer"]["activities_offered"])


def test_ack_retry_and_response_retry_keep_original_versions(coordinator):
    first = coordinator.evaluate("first", evidence())
    ack = deliver(coordinator, first, BASE)
    response = respond(coordinator, first, BASE, "rejected")
    assert deliver(coordinator, first, BASE) == {**ack, "replayed": True}
    assert respond(coordinator, first, BASE, "rejected") == {**response, "replayed": True}
    history = coordinator.history(evidence().profile_id)
    assert len(history["events"]) == 3
    with pytest.raises(ValueError, match="already has"):
        respond(coordinator, first, BASE, "postponed", "different-response")
    assert coordinator.history(evidence().profile_id) == history


def test_bedtime_across_midnight_uses_elapsed_time(coordinator):
    at = BASE.replace(hour=23, minute=30)
    result = coordinator.evaluate("midnight", evidence(at,
        bedtime_at=(at + timedelta(minutes=45)).isoformat()))
    assert result["offer"]["context"] == "bedtime"


def test_offsets_do_not_reset_rolling_cooldown(coordinator):
    completed(coordinator, BASE, 1)
    at = (BASE + timedelta(minutes=30)).astimezone(datetime.fromisoformat("2026-01-02T12:00:00+09:00").tzinfo)
    assert coordinator.evaluate("travel", evidence(at, "travel",
        bedtime_at=(at + timedelta(minutes=30)).isoformat()))["reason"] == "shared_cooldown"


def test_inactive_screen_recheck_never_promotes_overlay(coordinator):
    coordinator.evaluate("first", evidence(game_active=True))
    assert coordinator.evaluate("off", evidence(screen_interactive=False))["reason"] == "screen_inactive"


def test_selected_is_choice_not_completion_and_postponed_resets_streak(coordinator):
    completed(coordinator, BASE, 1, "rejected")
    completed(coordinator, BASE + timedelta(hours=2), 2, "postponed")
    at = BASE.replace(hour=20, minute=30)
    result = coordinator.evaluate("bed", evidence(at, "bedtime"))
    deliver(coordinator, result, at, "bed-delivery")
    selected = result["offer"]["activities_offered"][0]
    response = respond(coordinator, result, at, "selected", "bed-response", selected_activity_id=selected)
    assert response["offer"]["response"] == "selected"
    assert "completed" not in response["offer"]


def test_incomplete_receipts_fail_before_replay_or_new_offer(coordinator):
    import sqlite3
    coordinator.evaluate("first", evidence())
    with sqlite3.connect(coordinator.path) as db:
        db.execute("DELETE FROM receipts")
    with pytest.raises(ValueError, match="Incomplete receipt"):
        coordinator.evaluate("first", evidence())
    with pytest.raises(ValueError, match="Incomplete receipt"):
        ChildOfferCoordinator(coordinator.path)


def test_deletion_during_runtime_does_not_initialize_empty_database(coordinator):
    import sqlite3
    coordinator.path.unlink()
    with pytest.raises(sqlite3.OperationalError):
        coordinator.evaluate("first", evidence())
    assert not coordinator.path.exists()


def test_policy_type_change_is_not_accepted_as_numeric_equality(coordinator):
    import sqlite3
    with sqlite3.connect(coordinator.path) as db:
        state = json.loads(db.execute("SELECT body FROM state").fetchone()[0])
        state["policy"]["maximum_bedtime"] = True
        db.execute("UPDATE state SET body=?", (json.dumps(state),))
    with pytest.raises(ValueError, match="mismatch"):
        ChildOfferCoordinator(coordinator.path)


@pytest.mark.parametrize("now,bedtime,allowed", [
    ("2026-03-08T01:30:00-05:00", "2026-03-08T03:15:00-04:00", True),
    ("2026-11-01T01:30:00-04:00", "2026-11-01T01:45:00-05:00", False),
])
def test_dst_explicit_resolved_offsets_use_actual_elapsed_time(coordinator, now, bedtime, allowed):
    at = datetime.fromisoformat(now)
    result = coordinator.evaluate("dst", evidence(at, bedtime_at=bedtime))
    assert (result["status"] == "offer") == allowed


def test_early_bedtime_does_not_reopen_daytime_after_its_window(coordinator):
    at = BASE.replace(hour=19)
    next_bedtime = at.replace(hour=18) + timedelta(days=1)
    assert coordinator.evaluate("after-early-bed", evidence(at, bedtime_at=next_bedtime.isoformat()))["reason"] == "outside_trigger"
