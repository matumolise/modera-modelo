"""Contrato experimental para el agregado diario calculado por Android.

No se conecta al detector ni a la persistencia. Los metadatos permiten
comprobar coherencia, pero no reconstruir los minutos sin eventos crudos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contracts import Coverage, HistoricalRepresentation, ObservationStatus, Provenance
from .interactive_duration_v3 import ALGORITHM_VERSION


INTERACTIVE_SCREEN_SPEC_ID_V3 = "interactive_screen_device_minutes_v3_draft"
INTERACTIVE_SCREEN_PHENOMENON = "DEVICE_INTERACTIVE_SCREEN_DURATION"


def _epoch_ms(timestamp: datetime) -> int:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Los instantes requieren zona horaria.")
    millis = timestamp.timestamp() * 1000
    if not math.isfinite(millis) or abs(millis - round(millis)) > 0.01:
        raise ValueError("Los instantes requieren precisión de milisegundos.")
    return round(millis)


@dataclass(frozen=True)
class QueryWindowV3:
    run_id: str
    begin_epoch_ms: int
    end_epoch_ms: int
    succeeded: bool

    def __post_init__(self) -> None:
        if (not isinstance(self.run_id, str) or not self.run_id.strip()
                or type(self.begin_epoch_ms) is not int
                or type(self.end_epoch_ms) is not int
                or type(self.succeeded) is not bool
                or self.begin_epoch_ms >= self.end_epoch_ms):
            raise ValueError("Ventana o run_id inválido.")


@dataclass(frozen=True)
class InitialStateV3:
    event_epoch_ms: int
    event_type_code: int  # 15 interactivo, 16 no interactivo

    def __post_init__(self) -> None:
        if (type(self.event_epoch_ms) is not int
                or type(self.event_type_code) is not int
                or self.event_type_code not in (15, 16)):
            raise ValueError("El estado inicial debe ser un evento de pantalla.")


@dataclass(frozen=True)
class AndroidInteractiveAggregateV3:
    capture_id: str
    device_id: str
    local_date: date
    time_zone_id: str
    interval_start: datetime
    interval_end: datetime
    computed_at: datetime
    algorithm_version: str
    status: ObservationStatus
    interactive_screen_minutes: float | None
    missing_reason: str | None
    initial_state: InitialStateV3 | None
    query_windows: tuple[QueryWindowV3, ...]
    restart_in_day: bool
    conflicting_overlaps: bool
    ambiguous_event_order: bool

    def __post_init__(self) -> None:
        if (not isinstance(self.capture_id, str) or not self.capture_id.strip()
                or not isinstance(self.device_id, str) or not self.device_id.strip()):
            raise ValueError("capture_id y device_id son obligatorios.")
        if (type(self.local_date) is not date
                or not isinstance(self.time_zone_id, str)
                or not isinstance(self.status, ObservationStatus)
                or any(type(flag) is not bool for flag in (
                    self.restart_in_day, self.conflicting_overlaps,
                    self.ambiguous_event_order))
                or not isinstance(self.query_windows, tuple)
                or any(not isinstance(q, QueryWindowV3) for q in self.query_windows)
                or (self.initial_state is not None
                    and not isinstance(self.initial_state, InitialStateV3))):
            raise ValueError("Tipos inválidos en la captura diaria.")
        if self.algorithm_version != ALGORITHM_VERSION:
            raise ValueError("Versión de algoritmo no reconocida.")
        try:
            zone = ZoneInfo(self.time_zone_id)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Zona IANA no reconocida.") from exc
        start = _epoch_ms(self.interval_start)
        end = _epoch_ms(self.interval_end)
        if start >= end or end > _epoch_ms(self.computed_at):
            raise ValueError("Intervalo diario o fecha de cálculo inválidos.")
        local_start = datetime.combine(self.local_date, time.min, tzinfo=zone)
        local_end = datetime.combine(date.fromordinal(self.local_date.toordinal() + 1), time.min, tzinfo=zone)
        if (start != _epoch_ms(local_start) or end != _epoch_ms(local_end)):
            raise ValueError("Los instantes no delimitan la fecha local indicada.")
        if len({q.run_id for q in self.query_windows}) != len(self.query_windows):
            raise ValueError("run_id repetido.")
        if self.status is ObservationStatus.NOT_APPLICABLE:
            raise ValueError("NOT_APPLICABLE no es un resultado del collector.")
        if self.status is ObservationStatus.MISSING:
            if self.interactive_screen_minutes is not None or not self.missing_reason:
                raise ValueError("MISSING requiere minutos nulos y motivo.")
        else:
            value = self.interactive_screen_minutes
            if (isinstance(value, bool) or not isinstance(value, (float, int))
                    or not math.isfinite(value) or value < 0 or value > (end - start) / 60000):
                raise ValueError("Minutos fuera del día o inválidos.")
            if self.missing_reason is not None:
                raise ValueError("Una observación válida no lleva motivo de faltante.")
            if (self.status is ObservationStatus.OBSERVED_ZERO) != (value == 0):
                raise ValueError("Cero y positivo deben tener estados distintos.")


def review_aggregate_v3(aggregate: AndroidInteractiveAggregateV3) -> tuple[ObservationStatus, float | None, str | None]:
    """Aplica abstenciones verificables sin asumir que Android es exhaustivo."""
    if aggregate.status is ObservationStatus.MISSING:
        return ObservationStatus.MISSING, None, aggregate.missing_reason
    if aggregate.initial_state is None or aggregate.initial_state.event_epoch_ms >= _epoch_ms(aggregate.interval_start):
        return ObservationStatus.MISSING, None, "INITIAL_STATE_UNKNOWN"
    if aggregate.restart_in_day:
        return ObservationStatus.MISSING, None, "RESTART_IN_DAY"
    if aggregate.conflicting_overlaps:
        return ObservationStatus.MISSING, None, "CONFLICTING_OVERLAPPING_QUERIES"
    if aggregate.ambiguous_event_order:
        return ObservationStatus.MISSING, None, "AMBIGUOUS_EVENT_ORDER"
    start = aggregate.initial_state.event_epoch_ms
    end = _epoch_ms(aggregate.interval_end)
    cursor = start
    windows = sorted((q for q in aggregate.query_windows if q.succeeded),
                     key=lambda q: (q.begin_epoch_ms, q.end_epoch_ms))
    for query in windows:
        if query.begin_epoch_ms > cursor:
            break
        cursor = max(cursor, query.end_epoch_ms)
        if cursor >= end:
            break
    if cursor < end:
        return ObservationStatus.MISSING, None, "INCOMPLETE_QUERY_COVERAGE"
    return aggregate.status, aggregate.interactive_screen_minutes, None


def adapt_interactive_aggregate_v3(
    aggregate: AndroidInteractiveAggregateV3, *, representation_record_id: str,
) -> HistoricalRepresentation:
    """Representación aislada de uso del dispositivo; aún no alimentar C1."""
    status, minutes, reason = review_aggregate_v3(aggregate)
    return HistoricalRepresentation(
        representation_record_id=representation_record_id,
        representation_spec_id=INTERACTIVE_SCREEN_SPEC_ID_V3,
        subject_id=aggregate.device_id,
        phenomenon=INTERACTIVE_SCREEN_PHENOMENON,
        interval_start=aggregate.interval_start,
        interval_end=aggregate.interval_end,
        value=minutes,
        unit="minutes",
        status=status,
        coverage=Coverage(value=None, basis="query_windows_not_event_exhaustiveness"),
        quality_flags=("DEVICE_LEVEL_ONLY", "PARITY_PENDING", *((reason,) if reason else ())),
        provenance=Provenance(
            source_id=aggregate.capture_id,
            source_version=aggregate.algorithm_version,
            source_semantics="screen_interactive_device_not_attention_or_child_use",
            adapter_version="v3-draft",
        ),
        computed_at=aggregate.computed_at,
    )
