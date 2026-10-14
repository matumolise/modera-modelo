"""Automatic offers: atomic reference coordinator, without UI or capture code.

Policy values are engineering decisions, not clinical recommendations. Inputs
must be supplied by a trusted capture/identity adapter. Never infer delivery.
"""
from contextlib import closing, contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from analytics_service.activities import select_activities
from recommendations import ACTIVITY_CATALOG, ActivityEligibility, recommend_activities

POLICY = {
    "version": "automatic-child-offers-v1-engineering",
    "day_start_hour": 8, "day_end_hour": 20, "continuous_minutes": 45,
    "bedtime_minutes": 60, "cooldown_minutes": 120,
    "maximum_total": 3, "maximum_daytime": 2, "maximum_bedtime": 1,
    "ttl_minutes": 10, "rejection_pause_hours": 24,
}


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _time(value):
    if not isinstance(value, str):
        raise ValueError("An aware ISO timestamp is required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Naive timestamps are not accepted")
    return parsed


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat()


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value):
        raise ValueError("Invalid scoped identifier")


def _day_window(now, bedtime):
    # End daytime offers at the configured bedtime window, including early beds.
    bed_minutes = bedtime.hour * 60 + bedtime.minute
    end = POLICY["day_end_hour"] * 60
    if bed_minutes >= POLICY["day_start_hour"] * 60:
        end = min(end, bed_minutes - POLICY["bedtime_minutes"])
    return POLICY["day_start_hour"] * 60 <= now.hour * 60 + now.minute < end


def _stored_state(db):
    try:
        state = json.loads(db.execute("SELECT body FROM state WHERE id=1").fetchone()[0])
        count = db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    except (sqlite3.Error, TypeError, ValueError) as error:
        raise ValueError("Incomplete coordinator store; recovery is required") from error
    if (not isinstance(state, dict) or _json(state.get("policy")) != _json(POLICY)
            or not isinstance(state.get("profiles"), dict)):
        raise ValueError("Store policy/schema mismatch; explicit migration is required")
    if type(state.get("receipt_count")) is not int or state["receipt_count"] != count:
        raise ValueError("Incomplete receipt history; recovery is required")
    return state


@dataclass(frozen=True)
class OfferEvidence:
    profile_id: str
    series_id: str
    interval_id: str
    now: str
    interval_started_at: str
    bedtime_at: str
    automatic_enabled: bool
    assignment_verified: bool
    shared_phone: bool
    capture_verified: bool
    screen_interactive: bool
    game_active: bool
    in_school_period: bool
    eligibility_state: str
    eligibility: dict | None = None
    interests: tuple[str, ...] = ()


class ChildOfferCoordinator:
    """One SQLite transaction covers state, audit events and original receipts.

    A profile ID is globally scoped, never a bare legacy child integer. Each
    continuous interval has a stable ID and must end on a verified screen-off
    transition in the caller. Restart is not an interval boundary.
    """

    def __init__(self, path, *, create=False):
        self.path = Path(path)
        existed = self.path.exists()
        if not existed and not create:
            raise ValueError("Coordinator store missing; explicit initialization is required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not existed and not tables:
                db.execute("CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
                db.execute("CREATE TABLE receipts (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, body TEXT NOT NULL)")
                db.execute("INSERT INTO state VALUES (1, ?)", (_json({"policy": POLICY, "profiles": {}, "receipt_count": 0}),))
            _stored_state(db)

    @contextmanager
    def _transaction(self):
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db

    def _run(self, request_id, payload, now, operation):
        _identifier(request_id)
        fingerprint = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
        with self._transaction() as db:
            state = _stored_state(db)
            previous = db.execute("SELECT fingerprint, body FROM receipts WHERE id=?", (request_id,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise ValueError("Request ID reused with different evidence")
                return {**json.loads(previous[1]), "replayed": True}
            profile = state["profiles"].setdefault(payload["profile_id"], {
                "clock": None, "intervals": {}, "offers": [], "events": [],
            })
            if profile["clock"] and now < _time(profile["clock"]):
                raise ValueError("Processing clock moved backwards")
            result = operation(profile)
            profile["clock"] = _stamp(now)
            result = json.loads(_json({**result, "policy_version": POLICY["version"], "replayed": False}))
            state["receipt_count"] += 1
            db.execute("UPDATE state SET body=? WHERE id=1", (_json(state),))
            db.execute("INSERT INTO receipts VALUES (?, ?, ?)", (request_id, fingerprint, _json(result)))
            return deepcopy(result)

    @staticmethod
    def _expire(profile, now):
        for offer in profile["offers"]:
            if offer["status"] in {"pending", "delivered"} and now >= _time(offer["expires_at"]):
                offer["status"] = "delivery_unknown" if offer["delivered_at"] is None else "ignored"
                profile["events"].append({"offer_id": offer["offer_id"], "event": offer["status"], "at": _stamp(now)})

    @staticmethod
    def _guard(evidence):
        for flag, reason in (
            (not evidence.automatic_enabled, "automatic_disabled"),
            (not evidence.assignment_verified or evidence.shared_phone, "identity_uncertain"),
            (not evidence.capture_verified, "capture_unverified"),
            (not evidence.screen_interactive, "screen_inactive"),
            (evidence.in_school_period, "school_period"),
            (evidence.eligibility_state != "known", "eligibility_unknown"),
        ):
            if flag:
                return reason
        return None

    def evaluate(self, request_id, evidence: OfferEvidence):
        if not isinstance(evidence, OfferEvidence):
            raise ValueError("OfferEvidence is required")
        payload = asdict(evidence)
        evidence = OfferEvidence(**payload)  # Freeze caller-owned mutable filters.
        for key in ("profile_id", "series_id", "interval_id"):
            _identifier(payload[key])
        for key in ("automatic_enabled", "assignment_verified", "shared_phone", "capture_verified",
                    "screen_interactive", "game_active", "in_school_period"):
            if type(payload[key]) is not bool:
                raise ValueError("Evidence flags must be booleans")
        now, start, bedtime = map(_time, (evidence.now, evidence.interval_started_at, evidence.bedtime_at))
        if start > now:
            raise ValueError("Interval starts after processing time")
        # Existing adapter validates eligibility and vocabulary; no duplicated filters.
        selection_request = {"request_id": request_id, "context": "general",
                             "interests": list(evidence.interests), "eligibility_state": evidence.eligibility_state}
        if evidence.eligibility is not None:
            selection_request["eligibility"] = evidence.eligibility
        def operation(profile):
            select_activities(selection_request)
            self._expire(profile, now)
            key = evidence.series_id + ":" + evidence.interval_id
            previous_start = profile["intervals"].setdefault(key, _stamp(start))
            if previous_start != _stamp(start):
                raise ValueError("Interval identity changed its original start")
            reason = self._guard(evidence)
            if reason:
                return {"status": "suppressed", "reason": reason}
            pending = [o for o in profile["offers"] if o["status"] in {"pending", "delivery_unknown", "delivered"}]
            if pending:
                offer = pending[-1]
                if offer["status"] == "delivery_unknown":
                    return {"status": "suppressed", "reason": "delivery_reconciliation_required", "offer_id": offer["offer_id"]}
                if offer["opportunity"] != key:
                    return {"status": "suppressed", "reason": "outstanding_offer"}
                bed_now = timedelta(0) <= bedtime - now <= timedelta(minutes=POLICY["bedtime_minutes"])
                if ((offer["context"] == "bedtime") != bed_now
                        or (not bed_now and not _day_window(now, bedtime))):
                    return {"status": "suppressed", "reason": "presentation_context_changed"}
                channel = "notification" if evidence.game_active else "overlay"
                if offer["delivered_at"] is None and channel != offer["initial_channel"]:
                    return {"status": "suppressed", "reason": "pending_delivery_confirmation"}
                # Recheck eligibility of the frozen list before presentation on another channel.
                eligible = {a.activity_id for a in recommend_activities(
                    offer["context"], eligibility=ActivityEligibility(**evidence.eligibility),
                    n=len(ACTIVITY_CATALOG), random_seed=0,
                )}
                if not set(offer["activities_offered"]).issubset(eligible):
                    return {"status": "suppressed", "reason": "frozen_offer_no_longer_eligible"}
                return {"status": "offer", "offer": deepcopy(offer),
                        "channel": channel}
            if any(o["opportunity"] == key for o in profile["offers"]):
                return {"status": "suppressed", "reason": "opportunity_consumed"}
            responses = sorted((o for o in profile["offers"] if o["response"] not in {None, "ignored"}),
                               key=lambda o: o["response_at"])
            streak = 0
            for offer in responses:
                streak = streak + 1 if offer["response"] == "rejected" else 0
            if streak >= 2 and now < _time(responses[-1]["response_at"]) + timedelta(hours=POLICY["rejection_pause_hours"]):
                return {"status": "suppressed", "reason": "rejection_pause"}
            bed = timedelta(0) <= bedtime - now <= timedelta(minutes=POLICY["bedtime_minutes"])
            context = "bedtime" if bed else "general"
            if not bed and not (_day_window(now, bedtime)
                               and now - start >= timedelta(minutes=POLICY["continuous_minutes"])):
                return {"status": "suppressed", "reason": "outside_trigger"}
            delivered = [o for o in profile["offers"] if o["delivered_at"]]
            if delivered and now - max(_time(o["delivered_at"]) for o in delivered) < timedelta(minutes=POLICY["cooldown_minutes"]):
                return {"status": "suppressed", "reason": "shared_cooldown"}
            rolling = [o for o in delivered if now - _time(o["delivered_at"]) < timedelta(hours=24)]
            local = [o for o in delivered if _time(o["delivered_at"]).astimezone(now.tzinfo).date() == now.date()]
            limit = POLICY["maximum_bedtime"] if bed else POLICY["maximum_daytime"]
            if any(len(group) >= POLICY["maximum_total"] or sum(o["context"] == context for o in group) >= limit
                   for group in (rolling, local)):
                return {"status": "suppressed", "reason": "automatic_quota"}
            recent = [a for o in delivered[-3:] for a in o["activities_offered"]]
            selection = select_activities({**selection_request, "context": context, "recently_shown_ids": recent})
            if not selection["activities"]:
                return {"status": "suppressed", "reason": "no_eligible_activities"}
            offer = {
                "offer_id": str(uuid4()), "profile_id": evidence.profile_id,
                "series_id": evidence.series_id, "interval_id": evidence.interval_id,
                "opportunity": key, "context": context,
                "source": "system_bedtime" if bed else "system_daytime",
                "created_at": _stamp(now), "expires_at": _stamp(now + timedelta(minutes=POLICY["ttl_minutes"])),
                "delivered_at": None, "status": "pending", "response": None, "response_at": None,
                "selected_activity_id": None, "channels": [], "selection": selection,
                "initial_channel": "notification" if evidence.game_active else "overlay",
                "activities_offered": [a["activity_id"] for a in selection["activities"]],
                "evidence": payload,
            }
            profile["offers"].append(offer)
            profile["events"].append({"offer_id": offer["offer_id"], "event": "generated", "at": _stamp(now)})
            return {"status": "offer", "offer": deepcopy(offer),
                    "channel": "notification" if evidence.game_active else "overlay"}

        return self._run(request_id, {"method": "evaluate", **payload}, now, operation)

    def record_event(self, request_id, *, profile_id, offer_id, event, occurred_at, now,
                     channel=None, selected_activity_id=None):
        _identifier(profile_id)
        _identifier(offer_id)
        actual, processing = _time(occurred_at), _time(now)
        if actual > processing:
            raise ValueError("Event occurs after processing time")
        if event not in {"delivered", "delivery_failed", "selected", "rejected", "postponed", "dismissed"}:
            raise ValueError("Unknown delivery/response event")
        if (event == "delivered" and channel not in {"notification", "overlay"}) or (event != "delivered" and channel is not None):
            raise ValueError("Invalid event channel")
        if event != "selected" and selected_activity_id is not None:
            raise ValueError("Only selected events have an activity ID")
        payload = {"method": "event", "profile_id": profile_id, "offer_id": offer_id, "event": event,
                   "occurred_at": occurred_at, "now": now, "channel": channel, "selected_activity_id": selected_activity_id}

        def operation(profile):
            offer = next((o for o in profile["offers"] if o["offer_id"] == offer_id), None)
            if not offer:
                raise ValueError("Offer does not belong to this profile")
            if actual < _time(offer["created_at"]):
                raise ValueError("Event precedes offer")
            if event == "delivered":
                if offer["status"] in {"failed", "responded"}:
                    raise ValueError("Terminal offer cannot be delivered")
                if actual >= _time(offer["expires_at"]):
                    raise ValueError("Expired offer cannot be displayed")
                if offer["delivered_at"] is None:
                    offer["delivered_at"] = _stamp(actual)
                    offer["expires_at"] = _stamp(actual + timedelta(minutes=POLICY["ttl_minutes"]))
                    offer["status"] = "delivered"
                elif actual < _time(offer["delivered_at"]):
                    raise ValueError("Delivery channels out of chronological order")
                if channel not in offer["channels"]:
                    offer["channels"].append(channel)
            elif event == "delivery_failed":
                if offer["delivered_at"] or offer["response"]:
                    raise ValueError("Confirmed delivery cannot be withdrawn")
                offer["status"] = "failed"
            else:
                if not offer["delivered_at"] or actual < _time(offer["delivered_at"]):
                    raise ValueError("Response requires prior confirmed delivery")
                response = "ignored" if event == "dismissed" else event
                if offer["response"] is not None:
                    raise ValueError("Offer already has a response")
                if actual >= _time(offer["expires_at"]):
                    raise ValueError("Response outside offer validity")
                if event == "selected" and selected_activity_id not in offer["activities_offered"]:
                    raise ValueError("Selected activity was not offered")
                offer.update(status="responded", response=response, response_at=_stamp(actual),
                             selected_activity_id=selected_activity_id)
            profile["events"].append({**payload, "at": _stamp(processing)})
            self._expire(profile, processing)
            return {"status": "recorded", "offer": deepcopy(offer)}

        return self._run(request_id, payload, processing, operation)

    def history(self, profile_id):
        _identifier(profile_id)
        with self._transaction() as db:
            state = _stored_state(db)
            return deepcopy(state["profiles"].get(profile_id, {"offers": [], "events": []}))
