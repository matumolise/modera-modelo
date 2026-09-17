"""Core contracts for Moderá's Historical Analyzer.

This module intentionally contains only structural/semantic contracts that are
already justified by Phase 12. It does not define product thresholds, CUSUM
parameters, baseline adaptation, reset/rearm rules, or alerting policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from numbers import Real
from typing import Any


class ObservationStatus(str, Enum):
    """Semantic state of an observation/representation value."""

    OBSERVED = "OBSERVED"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class Coverage:
    """Observed coverage without assuming that unknown means complete.

    ``basis`` remains a free semantic label for now because Phase 12-A and
    external dataset inspection still need to determine which coverage notions
    are actually measurable (for example temporal or attribution coverage).
    """

    value: float | None = None
    basis: str | None = None

    def __post_init__(self) -> None:
        if self.value is not None and not 0.0 <= float(self.value) <= 1.0:
            raise ValueError("coverage.value must be between 0 and 1")

        if self.basis is not None and not self.basis.strip():
            raise ValueError("coverage.basis cannot be blank")

    @property
    def is_known(self) -> bool:
        return self.value is not None

    @property
    def is_full(self) -> bool:
        return self.value is not None and float(self.value) == 1.0


@dataclass(frozen=True)
class Provenance:
    """Minimal provenance required to preserve source semantics/versioning."""

    source_id: str
    source_version: str | None = None
    source_semantics: str | None = None
    adapter_version: str | None = None
    input_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("provenance.source_id cannot be blank")


def _require_aware_timestamp(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate_interval(interval_start: datetime, interval_end: datetime) -> None:
    _require_aware_timestamp("interval_start", interval_start)
    _require_aware_timestamp("interval_end", interval_end)

    if interval_start >= interval_end:
        raise ValueError("interval_start must be before interval_end")


def _is_scalar_numeric_zero(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and float(value) == 0.0
    )


def _validate_status_value(status: ObservationStatus, value: Any) -> None:
    if status in {ObservationStatus.MISSING, ObservationStatus.NOT_APPLICABLE}:
        if value is not None:
            raise ValueError(f"{status.value} requires value=None")
        return

    if status is ObservationStatus.OBSERVED_ZERO:
        if not _is_scalar_numeric_zero(value):
            raise ValueError("OBSERVED_ZERO requires a scalar numeric zero")
        return

    if status is ObservationStatus.OBSERVED:
        if value is None:
            raise ValueError("OBSERVED requires a value")
        if _is_scalar_numeric_zero(value):
            raise ValueError("scalar zero must use OBSERVED_ZERO")
        return

    raise ValueError(f"Unsupported observation status: {status!r}")


@dataclass(frozen=True)
class BehavioralObservation:
    """Canonical observation of a behavioral phenomenon over an interval.

    ``interval_start``/``interval_end`` describe event/behavior time.
    ``computed_at`` describes processing time and must not redefine the
    behavioral interval, which is important for delayed collection/catch-up.
    """

    observation_id: str
    subject_id: str
    interval_start: datetime
    interval_end: datetime
    phenomenon: str
    value: Any
    unit: str | None
    status: ObservationStatus
    coverage: Coverage = field(default_factory=Coverage)
    quality_flags: tuple[str, ...] = ()
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )
    computed_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_interval(self.interval_start, self.interval_end)

        if self.computed_at is None:
            raise ValueError("computed_at is required")
        _require_aware_timestamp("computed_at", self.computed_at)

        if not self.observation_id.strip():
            raise ValueError("observation_id cannot be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id cannot be blank")
        if not self.phenomenon.strip():
            raise ValueError("phenomenon cannot be blank")

        _validate_status_value(self.status, self.value)


@dataclass(frozen=True)
class HistoricalRepresentation:
    """Versioned representation consumed later by reference/detector logic.

    Record identity is intentionally separate from representation-definition
    identity. The exact lineage mechanism remains open; provenance carries the
    minimum version/source information without freezing a full lineage model.
    """

    representation_record_id: str
    representation_spec_id: str
    subject_id: str
    phenomenon: str
    interval_start: datetime
    interval_end: datetime
    value: Any
    unit: str | None
    status: ObservationStatus
    coverage: Coverage = field(default_factory=Coverage)
    quality_flags: tuple[str, ...] = ()
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )
    computed_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_interval(self.interval_start, self.interval_end)

        if self.computed_at is None:
            raise ValueError("computed_at is required")
        _require_aware_timestamp("computed_at", self.computed_at)

        if not self.representation_record_id.strip():
            raise ValueError("representation_record_id cannot be blank")
        if not self.representation_spec_id.strip():
            raise ValueError("representation_spec_id cannot be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id cannot be blank")
        if not self.phenomenon.strip():
            raise ValueError("phenomenon cannot be blank")

        _validate_status_value(self.status, self.value)
