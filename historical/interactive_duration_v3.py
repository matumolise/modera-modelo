"""Referencia experimental v3 de minutos diarios de pantalla interactiva.

No reemplaza el adaptador v2 ni publica observaciones al histórico. Conserva
los eventos crudos y elige una consulta por tramo temporal, sin deduplicar
por timestamp/tipo. Si las consultas no permiten una reconstrucción inequívoca,
devuelve MISSING en lugar de convertir una ausencia en cero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from .android_usage import AndroidCollectorRunSummary, RawAndroidUsageEvent
from .contracts import ObservationStatus


SCREEN_INTERACTIVE = 15
SCREEN_NON_INTERACTIVE = 16
DEVICE_SHUTDOWN = 26
DEVICE_STARTUP = 27
RELEVANT_CODES = frozenset({
    SCREEN_INTERACTIVE, SCREEN_NON_INTERACTIVE, DEVICE_SHUTDOWN, DEVICE_STARTUP,
})
ALGORITHM_VERSION = "interactive-screen-reference-v3-draft"


@dataclass(frozen=True)
class InteractiveDayV3:
    status: ObservationStatus
    minutes: float | None
    missing_reason: str | None
    source_run_ids: tuple[str, ...]


def _missing(reason: str, run_ids: tuple[str, ...] = ()) -> InteractiveDayV3:
    return InteractiveDayV3(ObservationStatus.MISSING, None, reason, run_ids)


def _milliseconds(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Los límites del día requieren zona horaria.")
    milliseconds = value.timestamp() * 1000
    if not math.isfinite(milliseconds) or abs(milliseconds - round(milliseconds)) > 0.01:
        raise ValueError("Los límites deben tener precisión de milisegundos.")
    return round(milliseconds)


def _selected_segments(
    summaries: list[AndroidCollectorRunSummary], start: int, end: int,
) -> list[tuple[str, int, int]] | None:
    """Cubre el rango con el menor número de consultas, sin mezclar sus eventos."""
    segments: list[tuple[str, int, int]] = []
    cursor = start
    while cursor < end:
        candidates = [
            s for s in summaries
            if s.query_succeeded
            and s.requested_begin_epoch_ms <= cursor < s.requested_end_epoch_ms
        ]
        if not candidates:
            return None
        # Máxima extensión y luego colección más reciente; el ID desempata.
        chosen = sorted(
            candidates,
            key=lambda s: (-s.requested_end_epoch_ms,
                           -s.collected_at_epoch_ms, s.collector_run_id),
        )[0]
        next_cursor = min(end, chosen.requested_end_epoch_ms)
        segments.append((chosen.collector_run_id, cursor, next_cursor))
        cursor = next_cursor
    return segments


def _ordered_relevant(
    events: list[RawAndroidUsageEvent], begin: int, end: int,
) -> list[RawAndroidUsageEvent]:
    return sorted(
        (event for event in events
         if begin <= event.event_time_epoch_ms < end
         and event.event_type_code in RELEVANT_CODES),
        key=lambda event: (event.event_time_epoch_ms, event.query_ordinal),
    )


def _ambiguous_tie(events: list[RawAndroidUsageEvent]) -> bool:
    """El mismo ordinal no ordena tipos distintos en un mismo instante."""
    by_position: dict[tuple[int, int], int] = {}
    for event in events:
        position = (event.event_time_epoch_ms, event.query_ordinal)
        prior = by_position.setdefault(position, event.event_type_code)
        if prior != event.event_type_code:
            return True
    return False


def _conflicting_overlaps(
    summaries: list[AndroidCollectorRunSummary],
    by_run: dict[str, list[RawAndroidUsageEvent]],
    start: int, end: int,
) -> bool:
    successful = [s for s in summaries if s.query_succeeded]
    for index, left in enumerate(successful):
        for right in successful[index + 1:]:
            overlap_begin = max(start, left.requested_begin_epoch_ms,
                                right.requested_begin_epoch_ms)
            overlap_end = min(end, left.requested_end_epoch_ms,
                              right.requested_end_epoch_ms)
            if overlap_begin >= overlap_end:
                continue
            a = _ordered_relevant(by_run[left.collector_run_id], overlap_begin, overlap_end)
            b = _ordered_relevant(by_run[right.collector_run_id], overlap_begin, overlap_end)
            # Preservamos multiplicidad y secuencia; no suponemos identidad
            # única de dos eventos con igual timestamp y tipo.
            signature = lambda seq: [(e.event_time_epoch_ms, e.event_type_code) for e in seq]
            if signature(a) != signature(b):
                return True
    return False


def reconstruct_interactive_day_v3(
    *,
    interval_start: datetime,
    interval_end: datetime,
    raw_events: list[RawAndroidUsageEvent],
    summaries: list[AndroidCollectorRunSummary],
) -> InteractiveDayV3:
    """Calcula sólo días con estado inicial y cobertura comprobables.

    La versión v3 no infiere que un reboot dejó la pantalla apagada. Tampoco
    intenta identificar al niño que usó un dispositivo compartido.
    """
    start, end = _milliseconds(interval_start), _milliseconds(interval_end)
    if start >= end:
        raise ValueError("El comienzo debe preceder al fin del día.")

    by_summary: dict[str, AndroidCollectorRunSummary] = {}
    for summary in summaries:
        if summary.collector_run_id in by_summary:
            raise ValueError("collector_run_id repetido.")
        by_summary[summary.collector_run_id] = summary
    by_run: dict[str, list[RawAndroidUsageEvent]] = {key: [] for key in by_summary}
    for event in raw_events:
        summary = by_summary.get(event.collector_run_id)
        if summary is None or not summary.query_succeeded:
            raise ValueError("Evento sin consulta exitosa asociada.")
        if ((event.query_begin_epoch_ms, event.query_end_epoch_ms)
            != (summary.requested_begin_epoch_ms, summary.requested_end_epoch_ms)):
            raise ValueError("Ventana del evento incompatible con su consulta.")
        if not summary.requested_begin_epoch_ms <= event.event_time_epoch_ms < summary.requested_end_epoch_ms:
            raise ValueError("Evento fuera de su consulta.")
        by_run[event.collector_run_id].append(event)
    for summary in summaries:
        if len(by_run[summary.collector_run_id]) != summary.event_count:
            raise ValueError("event_count incompatible con la consulta.")

    predecessors = [
        event for event in raw_events
        if event.event_time_epoch_ms < start
        and event.event_type_code in RELEVANT_CODES
    ]
    if not predecessors:
        return _missing("INITIAL_STATE_UNKNOWN")
    candidate = max(predecessors, key=lambda e: (e.event_time_epoch_ms,
                                               e.query_ordinal))
    segments = _selected_segments(summaries, candidate.event_time_epoch_ms, end)
    if segments is None:
        return _missing("INCOMPLETE_QUERY_COVERAGE")
    run_ids = tuple(dict.fromkeys(run_id for run_id, _, _ in segments))
    if _conflicting_overlaps(summaries, by_run, candidate.event_time_epoch_ms, end):
        return _missing("CONFLICTING_OVERLAPPING_QUERIES", run_ids)

    events: list[RawAndroidUsageEvent] = []
    for run_id, begin, finish in segments:
        events.extend(_ordered_relevant(by_run[run_id], begin, finish))
    if _ambiguous_tie(events):
        return _missing("AMBIGUOUS_EVENT_ORDER", run_ids)

    state: int | None = None
    interactive_since: int | None = None
    duration_ms = 0
    for event in events:
        timestamp, code = event.event_time_epoch_ms, event.event_type_code
        if code in (DEVICE_SHUTDOWN, DEVICE_STARTUP):
            if start <= timestamp < end:
                reason = ("OPEN_INTERVAL_ACROSS_RESTART" if state == SCREEN_INTERACTIVE
                          else "UNKNOWN_STATE_AFTER_RESTART")
                return _missing(reason, run_ids)
            state = None
            interactive_since = None
            continue
        if timestamp < start:
            state = code
            continue
        if state is None:
            return _missing("INITIAL_STATE_UNKNOWN", run_ids)
        if code == SCREEN_INTERACTIVE:
            if state != SCREEN_INTERACTIVE:
                interactive_since = timestamp
            state = SCREEN_INTERACTIVE
        else:
            if state == SCREEN_INTERACTIVE:
                duration_ms += timestamp - (interactive_since if interactive_since is not None else start)
                interactive_since = None
            state = SCREEN_NON_INTERACTIVE
    if state is None:
        return _missing("INITIAL_STATE_UNKNOWN", run_ids)
    if state == SCREEN_INTERACTIVE:
        duration_ms += end - (interactive_since if interactive_since is not None else start)
    minutes = duration_ms / 60000.0
    status = (ObservationStatus.OBSERVED_ZERO if duration_ms == 0
              else ObservationStatus.OBSERVED)
    return InteractiveDayV3(status, minutes, None, run_ids)
