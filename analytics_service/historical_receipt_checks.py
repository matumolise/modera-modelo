"""Valida recibos existentes sin regenerarlos, escribirlos ni cambiar la política C1."""

from dataclasses import asdict
import math

from historical.detector import evaluate_c1
from historical.emitter import decide_detection_event


def _finite(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError("Numero de recibo no finito o de tipo incompatible")


def validate_receipt_semantics(
    record, previous, result, profile, expected_history_count
):
    """Comprueba ecuaciones contra la referencia guardada, no reconstruye otra referencia.

    La auditoria offline completa contrasta además mediana/MAD con la historia.
    Reusar IDs y fechas aquí sólo valida el recibo: nunca se devuelve ni persiste
    el objeto recalculado en lugar del original.
    """
    ref, ev = result.reference, result.evaluation
    if (
        type(ref.history_count) is not int
        or ref.history_count != expected_history_count
        or type(ev.reference_history_count) is not int
        or type(ev.detector_min_history) is not int
    ):
        raise ValueError("Conteo de historia del recibo incompatible")
    for value in (
        ref.location,
        ref.scale,
        ev.observed_value,
        ev.reference_location,
        ev.reference_scale,
        ev.detector_statistic,
        ev.positive_cusum,
        ev.negative_cusum,
        previous.previous_eligible_statistic,
        result.next_state.previous_eligible_statistic,
    ):
        _finite(value, nullable=True)
    for value in (
        ev.detector_k,
        ev.threshold,
        previous.cusum_state.positive,
        previous.cusum_state.negative,
        result.next_state.cusum_state.positive,
        result.next_state.cusum_state.negative,
    ):
        _finite(value)
    expected = evaluate_c1(
        record,
        ref,
        previous.cusum_state,
        profile.config,
        evaluation_id=ev.evaluation_id,
        analysis_version=profile.analysis_version,
        computed_at=ev.computed_at,
    )
    if (
        asdict(expected.evaluation) != asdict(ev)
        or expected.next_state != result.next_state.cusum_state
    ):
        raise ValueError(
            "Evaluacion del recibo incompatible con entrada, referencia o estado previo"
        )
    event = result.emission.event
    emission = decide_detection_event(
        ev,
        previous_statistic=previous.previous_eligible_statistic,
        event_id=event.event_id if event else ev.evaluation_id,
        emitter_version=profile.emitter_version,
        emitted_at=event.emitted_at if event else ev.computed_at,
    )
    if emission != result.emission:
        raise ValueError("Emision del recibo incompatible con el cruce observado")
