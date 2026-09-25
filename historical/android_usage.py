"""Adaptación de eventos raw de Android al dominio histórico de Moderá."""

from dataclasses import dataclass
from datetime import datetime, timezone

from .contracts import BehavioralObservation, Provenance
from .daily_usage import (
    PreparedInteractiveDurationWindow,
    ScreenStateEvent,
    ScreenStateEventType,
    build_daily_use_observation,
    calculate_interactive_duration,
    prepare_interactive_duration_window,
)


RAW_USAGE_EVENT_SCHEMA_V1 = "raw-usage-event-v1"


@dataclass(frozen=True)
class RawAndroidUsageEvent:
    """Representa un evento raw exportado por el collector Android."""

    schema_version: str
    collector_run_id: str
    query_begin_epoch_ms: int
    query_end_epoch_ms: int
    collected_at_epoch_ms: int
    event_time_epoch_ms: int
    event_type_code: int
    event_type_name: str
    query_ordinal: int

    def __post_init__(self) -> None:
        if self.schema_version != RAW_USAGE_EVENT_SCHEMA_V1:
            raise ValueError(
                f"schema_version no soportado: {self.schema_version!r}."
            )

        if not self.collector_run_id.strip():
            raise ValueError("collector_run_id no puede estar vacío.")

        if self.query_begin_epoch_ms >= self.query_end_epoch_ms:
            raise ValueError(
                "query_begin_epoch_ms debe ser anterior a query_end_epoch_ms."
            )

        if self.query_ordinal < 0:
            raise ValueError("query_ordinal no puede ser negativo.")


def map_screen_state_event(
    raw_event: RawAndroidUsageEvent,
) -> ScreenStateEvent | None:
    """
    Convierte únicamente los eventos de estado de pantalla utilizados
    por el primer vertical histórico.

    Los demás tipos se conservan fuera de esta transformación y no se
    reinterpretan como uso, apertura de aplicación o sesión.
    """

    event_type_by_name = {
        "SCREEN_INTERACTIVE": ScreenStateEventType.INTERACTIVE,
        "SCREEN_NON_INTERACTIVE": ScreenStateEventType.NON_INTERACTIVE,
    }

    event_type = event_type_by_name.get(raw_event.event_type_name)
    if event_type is None:
        return None

    occurred_at = datetime.fromtimestamp(
        raw_event.event_time_epoch_ms / 1000.0,
        tz=timezone.utc,
    )

    return ScreenStateEvent(
        occurred_at=occurred_at,
        event_type=event_type,
    )

@dataclass(frozen=True)
class AndroidCollectorRunSummary:
    """Representa el resumen exportado por una ejecución del collector Android."""

    collector_run_id: str
    requested_begin_epoch_ms: int
    requested_end_epoch_ms: int
    collected_at_epoch_ms: int
    usage_access_available: bool
    query_returned_null: bool
    event_count: int
    error_code: str | None
    error_message: str | None

    def __post_init__(self) -> None:
        if not self.collector_run_id.strip():
            raise ValueError("collector_run_id no puede estar vacío.")

        if self.requested_begin_epoch_ms >= self.requested_end_epoch_ms:
            raise ValueError(
                "requested_begin_epoch_ms debe ser anterior a "
                "requested_end_epoch_ms."
            )

        if self.event_count < 0:
            raise ValueError("event_count no puede ser negativo.")

    @property
    def query_succeeded(self) -> bool:
        """
        Indica que Android pudo ejecutar la consulta.

        Esto no implica que la ventana consultada cubra un día completo
        ni que exista información suficiente para reconstruir sus límites.
        """
        return (
            self.usage_access_available
            and not self.query_returned_null
            and self.error_code is None
        )

@dataclass(frozen=True)
class DailyCaptureEvidence:
    """Resume la evidencia disponible para reconstruir un intervalo diario."""

    continuous_query_coverage: bool
    initial_state_known: bool

    @property
    def sufficient_for_reconstruction(self) -> bool:
        """
        Indica si existe evidencia suficiente para la reconstrucción operativa.

        No implica que Android garantice exhaustividad absoluta de sus eventos.
        """
        return (
            self.continuous_query_coverage
            and self.initial_state_known
        )


def evaluate_daily_capture_evidence(
    *,
    summaries: list[AndroidCollectorRunSummary],
    prepared_window: PreparedInteractiveDurationWindow,
    target_begin_epoch_ms: int,
    target_end_epoch_ms: int,
) -> DailyCaptureEvidence:
    """Evalúa por separado cobertura temporal y conocimiento del estado inicial."""

    return DailyCaptureEvidence(
        continuous_query_coverage=has_continuous_query_coverage(
            summaries=summaries,
            target_begin_epoch_ms=target_begin_epoch_ms,
            target_end_epoch_ms=target_end_epoch_ms,
        ),
        initial_state_known=prepared_window.initial_state_known,
    )

def build_daily_use_observation_from_android(
    *,
    observation_id: str,
    subject_id: str,
    interval_start: datetime,
    interval_end: datetime,
    computed_at: datetime,
    events: list[ScreenStateEvent],
    summaries: list[AndroidCollectorRunSummary],
    provenance: Provenance,
) -> BehavioralObservation:
    """
    Construye una observación diaria a partir de evidencia normalizada de Android.

    Una consulta exitosa no se considera por sí sola captura suficiente.
    Se exige cobertura temporal continua y un estado inicial conocido.
    """

    prepared_window = prepare_interactive_duration_window(
        events=events,
        interval_start=interval_start,
        interval_end=interval_end,
    )

    target_begin_epoch_ms = int(interval_start.timestamp() * 1000)
    target_end_epoch_ms = int(interval_end.timestamp() * 1000)

    evidence = evaluate_daily_capture_evidence(
        summaries=summaries,
        prepared_window=prepared_window,
        target_begin_epoch_ms=target_begin_epoch_ms,
        target_end_epoch_ms=target_end_epoch_ms,
    )

    reconstruction = calculate_interactive_duration(
        list(prepared_window.events)
    )

    return build_daily_use_observation(
        observation_id=observation_id,
        subject_id=subject_id,
        interval_start=interval_start,
        interval_end=interval_end,
        computed_at=computed_at,
        reconstruction=reconstruction,
        capture_complete=evidence.sufficient_for_reconstruction,
        provenance=provenance,
    )

def build_daily_use_observation_from_raw_android(
    *,
    observation_id: str,
    subject_id: str,
    interval_start: datetime,
    interval_end: datetime,
    computed_at: datetime,
    raw_events: list[RawAndroidUsageEvent],
    summaries: list[AndroidCollectorRunSummary],
    provenance: Provenance,
) -> BehavioralObservation:
    """
    Construye una observación diaria desde eventos raw exportados por Android.

    Sólo los eventos de estado de pantalla reconocidos por el primer vertical
    histórico se normalizan. Los demás tipos no se reinterpretan como uso.
    """

    summaries_by_run_id = {
        summary.collector_run_id: summary
        for summary in summaries
    }

    for raw_event in raw_events:
        summary = summaries_by_run_id.get(raw_event.collector_run_id)

        if summary is None:
            raise ValueError(
                "Cada evento raw debe tener un collector run asociado."
            )

        if (
            raw_event.query_begin_epoch_ms != summary.requested_begin_epoch_ms
            or raw_event.query_end_epoch_ms != summary.requested_end_epoch_ms
        ):
            raise ValueError(
                "La ventana de consulta del evento raw no coincide "
                "con la de su collector run."
            )

    screen_state_events = []

    for raw_event in raw_events:
        mapped_event = map_screen_state_event(raw_event)

        if mapped_event is not None:
            screen_state_events.append(mapped_event)

    return build_daily_use_observation_from_android(
        observation_id=observation_id,
        subject_id=subject_id,
        interval_start=interval_start,
        interval_end=interval_end,
        computed_at=computed_at,
        events=screen_state_events,
        summaries=summaries,
        provenance=provenance,
    )

def has_continuous_query_coverage(
    *,
    summaries: list[AndroidCollectorRunSummary],
    target_begin_epoch_ms: int,
    target_end_epoch_ms: int,
) -> bool:
    """
    Indica si consultas exitosas cubren de forma continua el intervalo objetivo.

    La función evalúa únicamente cobertura temporal de consultas. No afirma
    que Android haya entregado todos los eventos posibles dentro de ellas.
    """

    if target_begin_epoch_ms >= target_end_epoch_ms:
        raise ValueError(
            "target_begin_epoch_ms debe ser anterior a target_end_epoch_ms."
        )

    successful_windows = sorted(
        (
            (
                summary.requested_begin_epoch_ms,
                summary.requested_end_epoch_ms,
            )
            for summary in summaries
            if summary.query_succeeded
        ),
        key=lambda window: (window[0], window[1]),
    )

    if not successful_windows:
        return False

    covered_until = target_begin_epoch_ms

    for window_begin, window_end in successful_windows:
        if window_end <= covered_until:
            continue

        if window_begin > covered_until:
            return False

        covered_until = max(covered_until, window_end)

        if covered_until >= target_end_epoch_ms:
            return True

    return False