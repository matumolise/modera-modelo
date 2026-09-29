"""Read offer/response pairs with verified exposure from intervention JSONL."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from intervention_history import RESPONSE_SELECTED, VALID_RESPONSES


@dataclass(frozen=True)
class LinkedOfferResponse:
    offer_id: str
    child_id: int
    source: str
    context: str
    activities_offered: tuple[str, ...]
    response: str
    selected_activity_id: str | None


def _identity(value: object, line_number: int, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Line {line_number}: invalid {field}.")
    return value


def _offer_fields(event: dict, line_number: int) -> tuple[int, str, str, tuple[str, ...]]:
    child_id = event.get("child_id")
    if type(child_id) is not int or child_id <= 0:
        raise ValueError(f"Line {line_number}: invalid child_id.")
    source = _identity(event.get("source"), line_number, "source")
    context = _identity(event.get("context"), line_number, "context")
    offered = event.get("activities_offered")
    if not isinstance(offered, list) or not offered:
        raise ValueError(f"Line {line_number}: invalid activities_offered.")
    activities = tuple(
        _identity(activity, line_number, "activity_id") for activity in offered
    )
    if len(activities) != len(set(activities)):
        raise ValueError(f"Line {line_number}: duplicate activity_id.")
    return child_id, source, context, activities


def read_linked_offer_responses(
    input_path: str | Path,
) -> tuple[LinkedOfferResponse, ...]:
    """Return only verified pairs; legacy and unlinked responses give no signal.

    A linked response must occur after its offer in the same stream, describe
    the same child and offered activities, and be the only response to it.
    """
    offers: dict[str, tuple[int, str, str, tuple[str, ...]]] = {}
    answered: set[str] = set()
    linked: list[LinkedOfferResponse] = []

    with Path(input_path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Line {line_number}: invalid JSON.") from error
            if not isinstance(event, dict):
                raise ValueError(f"Line {line_number}: expected an object.")

            if "event_type" not in event:
                # Historical response rows predate offers and cannot prove exposure.
                if "response" not in event or "offer_id" in event:
                    raise ValueError(f"Line {line_number}: invalid legacy row.")
                continue
            kind = event["event_type"]
            if kind == "offer":
                offer_id = _identity(event.get("offer_id"), line_number, "offer_id")
                if offer_id in offers:
                    raise ValueError(f"Line {line_number}: duplicate offer_id.")
                offers[offer_id] = _offer_fields(event, line_number)
                continue
            if kind != "response":
                raise ValueError(f"Line {line_number}: unknown event_type.")

            offer_id = event.get("offer_id")
            if offer_id is None:
                # Current legacy API can still write an unlinked response.
                continue
            offer_id = _identity(offer_id, line_number, "offer_id")
            if offer_id not in offers:
                raise ValueError(f"Line {line_number}: missing prior offer.")
            if offer_id in answered:
                raise ValueError(f"Line {line_number}: duplicate response for offer.")

            child_id, source, context, activities = _offer_fields(event, line_number)
            if (child_id, source, context, activities) != offers[offer_id]:
                raise ValueError(f"Line {line_number}: response differs from offer.")
            response = event.get("response")
            if not isinstance(response, str) or response not in VALID_RESPONSES:
                raise ValueError(f"Line {line_number}: invalid response.")
            selected = event.get("selected_activity_id")
            if response == RESPONSE_SELECTED:
                if selected not in activities:
                    raise ValueError(f"Line {line_number}: selection was not offered.")
            elif selected is not None:
                raise ValueError(f"Line {line_number}: unexpected selection.")

            answered.add(offer_id)
            linked.append(
                LinkedOfferResponse(
                    offer_id=offer_id,
                    child_id=child_id,
                    source=source,
                    context=context,
                    activities_offered=activities,
                    response=response,
                    selected_activity_id=selected,
                )
            )
    return tuple(linked)
