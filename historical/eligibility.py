"""Eligibility decisions for Moderá's Historical Analyzer.

Reference inclusion is deliberately separated from current-time analysis
eligibility so cold-start observations can build history before the detector is
mature enough to run.

Coverage thresholds and quality-flag exclusion policy are intentionally absent
from this module version because Phase 12 has not frozen them yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real
from typing import Any

from .contracts import HistoricalRepresentation, ObservationStatus


class ReferenceInclusionReason(str, Enum):
    INCLUDED = "INCLUDED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NON_FINITE_VALUE = "NON_FINITE_VALUE"


@dataclass(frozen=True)
class ReferenceInclusionDecision:
    reason: ReferenceInclusionReason

    @property
    def included(self) -> bool:
        return self.reason is ReferenceInclusionReason.INCLUDED


class AnalysisEligibilityReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CURRENT_MISSING = "CURRENT_MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CURRENT_NON_FINITE = "CURRENT_NON_FINITE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    NON_ESTIMABLE_REFERENCE = "NON_ESTIMABLE_REFERENCE"


@dataclass(frozen=True)
class AnalysisEligibilityDecision:
    reason: AnalysisEligibilityReason
    reference_history_count: int

    @property
    def eligible(self) -> bool:
        return self.reason is AnalysisEligibilityReason.ELIGIBLE


def _is_non_finite_scalar(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and not math.isfinite(float(value))
    )


def decide_reference_inclusion(
    representation: HistoricalRepresentation,
) -> ReferenceInclusionDecision:
    """Decide whether a record may contribute a value to reference history.

    This decision never depends on history maturity. In particular, a valid
    cold-start observation can be included even when no detector evaluation is
    yet possible.
    """

    if representation.status is ObservationStatus.MISSING:
        return ReferenceInclusionDecision(ReferenceInclusionReason.MISSING)

    if representation.status is ObservationStatus.NOT_APPLICABLE:
        return ReferenceInclusionDecision(
            ReferenceInclusionReason.NOT_APPLICABLE
        )

    if _is_non_finite_scalar(representation.value):
        return ReferenceInclusionDecision(
            ReferenceInclusionReason.NON_FINITE_VALUE
        )

    return ReferenceInclusionDecision(ReferenceInclusionReason.INCLUDED)


def decide_analysis_eligibility(
    current: HistoricalRepresentation,
    *,
    reference_history_count: int,
    min_history: int,
    reference_estimable: bool,
) -> AnalysisEligibilityDecision:
    """Decide whether the detector may evaluate the current representation.

    ``min_history`` is mandatory and explicit. This function deliberately has
    no product default because numerical maturity remains an open Phase 12
    decision.
    """

    if reference_history_count < 0:
        raise ValueError("reference_history_count cannot be negative")
    if min_history < 1:
        raise ValueError("min_history must be at least 1")

    if current.status is ObservationStatus.MISSING:
        reason = AnalysisEligibilityReason.CURRENT_MISSING
    elif current.status is ObservationStatus.NOT_APPLICABLE:
        reason = AnalysisEligibilityReason.NOT_APPLICABLE
    elif _is_non_finite_scalar(current.value):
        reason = AnalysisEligibilityReason.CURRENT_NON_FINITE
    elif reference_history_count < min_history:
        reason = AnalysisEligibilityReason.INSUFFICIENT_HISTORY
    elif not reference_estimable:
        reason = AnalysisEligibilityReason.NON_ESTIMABLE_REFERENCE
    else:
        reason = AnalysisEligibilityReason.ELIGIBLE

    return AnalysisEligibilityDecision(
        reason=reason,
        reference_history_count=reference_history_count,
    )
