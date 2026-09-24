"""Adaptadores entre observaciones del producto y representaciones históricas."""

from __future__ import annotations

from .contracts import (
    BehavioralObservation,
    HistoricalRepresentation,
    Provenance,
)


DAILY_USE_DURATION_PHENOMENON = "DAILY_USE_DURATION"
DAILY_USE_DURATION_SPEC_ID = "daily_use_duration_minutes_v1"
DAILY_USE_DURATION_ADAPTER_VERSION = "v1"


def adapt_daily_use_duration(
    observation: BehavioralObservation,
    *,
    representation_record_id: str,
) -> HistoricalRepresentation:
    """Convierte una observación de uso diario en su representación histórica."""

    if observation.phenomenon != DAILY_USE_DURATION_PHENOMENON:
        raise ValueError(
            "La observación no corresponde a duración diaria de uso."
        )

    if observation.unit != "minutes":
        raise ValueError(
            "La duración diaria de uso debe expresarse en minutos."
        )

    provenance = Provenance(
        source_id=observation.provenance.source_id,
        source_version=observation.provenance.source_version,
        source_semantics=observation.provenance.source_semantics,
        adapter_version=DAILY_USE_DURATION_ADAPTER_VERSION,
        input_fingerprint=observation.provenance.input_fingerprint,
    )

    return HistoricalRepresentation(
        representation_record_id=representation_record_id,
        representation_spec_id=DAILY_USE_DURATION_SPEC_ID,
        subject_id=observation.subject_id,
        phenomenon=observation.phenomenon,
        interval_start=observation.interval_start,
        interval_end=observation.interval_end,
        value=observation.value,
        unit=observation.unit,
        status=observation.status,
        coverage=observation.coverage,
        quality_flags=observation.quality_flags,
        provenance=provenance,
        computed_at=observation.computed_at,
    )
