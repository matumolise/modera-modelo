"""Prequential scalar reference construction for Moderá's Historical Analyzer.

This module implements only the C1 scalar reference definition already retained
for Phase 12: median location and robust MAD scale over a caller-supplied set of
strictly prior usable records. Selection of that supplied history (for example
rolling vs expanding, post-detection inclusion, or other adaptation policy) is
external and remains open. This module deliberately does not define product
history maturity, coverage thresholds, detector thresholds, reset, or rearm
rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from numbers import Real
from statistics import median
from typing import Iterable

from .contracts import HistoricalRepresentation
from .eligibility import decide_reference_inclusion


MAD_NORMAL_CONSISTENCY = 1.4826


@dataclass(frozen=True)
class ScalarReference:
    """Robust scalar reference computed from records strictly prior to ``t``."""

    location: float | None
    scale: float | None
    history_count: int
    reference_cutoff: datetime

    @property
    def estimable(self) -> bool:
        return (
            self.location is not None
            and self.scale is not None
            and math.isfinite(self.location)
            and math.isfinite(self.scale)
            and self.scale > 0.0
        )


def _validate_same_series(
    current: HistoricalRepresentation,
    candidate: HistoricalRepresentation,
) -> None:
    if candidate.subject_id != current.subject_id:
        raise ValueError("history contains a different subject_id")
    if candidate.representation_spec_id != current.representation_spec_id:
        raise ValueError("history contains a different representation_spec_id")
    if candidate.phenomenon != current.phenomenon:
        raise ValueError("history contains a different phenomenon")
    if candidate.unit != current.unit:
        raise ValueError("history contains a different unit")


def _as_finite_scalar(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("scalar reference requires real numeric values")

    result = float(value)
    if not math.isfinite(result):
        raise ValueError("scalar reference requires finite numeric values")
    return result


def build_scalar_reference(
    current: HistoricalRepresentation,
    history: Iterable[HistoricalRepresentation],
) -> ScalarReference:
    """Build the robust C1 reference using event-time-prequential history.

    Only records whose interval ends at or before the current interval starts
    may contribute. Current, overlapping, and future records are ignored, so
    adding future observations cannot alter a historical reference.

    Reference inclusion semantics are delegated to ``decide_reference_inclusion``.
    Product maturity is intentionally not checked here; that belongs to
    ``AnalysisEligibility``. The caller also owns history-window/adaptation
    policy; this function only evaluates the records it is explicitly given.
    """

    values: list[float] = []

    for candidate in history:
        if candidate.interval_end > current.interval_start:
            continue

        _validate_same_series(current, candidate)

        if not decide_reference_inclusion(candidate).included:
            continue

        values.append(_as_finite_scalar(candidate.value))

    if not values:
        return ScalarReference(
            location=None,
            scale=None,
            history_count=0,
            reference_cutoff=current.interval_start,
        )

    location = float(median(values))
    absolute_deviations = [abs(value - location) for value in values]
    mad = float(median(absolute_deviations))
    scale = MAD_NORMAL_CONSISTENCY * mad

    return ScalarReference(
        location=location,
        scale=scale,
        history_count=len(values),
        reference_cutoff=current.interval_start,
    )
