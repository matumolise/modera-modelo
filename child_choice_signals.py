"""Count observed selections linked to recorded child activity offers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from intervention_history import RESPONSE_SELECTED
from intervention_history_reader import LinkedOfferResponse


def selected_activity_counts(
    interactions: Iterable[LinkedOfferResponse],
    child_id: int,
    context: str,
) -> dict[str, int]:
    """Count choices for one child/context; unchosen options give no signal."""
    if child_id <= 0:
        raise ValueError("child_id must be positive.")
    if not context:
        raise ValueError("context is required.")

    counts: Counter[str] = Counter()
    for interaction in interactions:
        if interaction.child_id != child_id or interaction.context != context:
            continue
        if interaction.response == RESPONSE_SELECTED:
            if interaction.selected_activity_id is None:
                raise ValueError("A selected response requires an activity_id.")
            counts[interaction.selected_activity_id] += 1
    return dict(counts)
