from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from historical.contracts import (
    Coverage,
    HistoricalRepresentation,
    ObservationStatus,
    Provenance,
)
from historical.detector import (
    C1DetectorConfig,
    CusumState,
    DetectorEvaluationOutcome,
    evaluate_c1,
)
from historical.reference import build_scalar_reference


EXPECTED_SHA256 = (
    "cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e"
)

METRIC_COLUMN = "totOnDurPerDayMin"
PHENOMENON = "TOTAL_USE_MINUTES"
UNIT = "minutes"
REPRESENTATION_SPEC_ID = "mediaticino.total_use.daily_minutes.f12c.v1"

# Experimental conditions only. These are NOT product parameters.
K_VALUES = (0.5, 1.0)
THRESHOLDS = (3.0, 5.0)
MIN_HISTORY = 7

# Perturbation expressed in subject-specific robust reference scales.
SHIFT_SCALES = (1.0, 2.0)
PERTURBATION_LENGTH = 3

UTC = timezone.utc
BASE_DATE = datetime(2020, 1, 1, tzinfo=UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(path: Path) -> pd.DataFrame:
    actual_hash = sha256_file(path)

    if actual_hash.lower() != EXPECTED_SHA256:
        raise SystemExit(f"Unexpected dataset SHA256: {actual_hash}")

    df = pd.read_csv(path, na_values=["-99"])

    normalized = [str(c).strip() for c in df.columns]
    if len(normalized) != len(set(normalized)):
        raise SystemExit(
            "Column-name normalization would create duplicate columns"
        )

    df.columns = normalized

    required = {"ID", "DayInStudy", METRIC_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    if df.duplicated(["ID", "DayInStudy"]).any():
        raise SystemExit("Duplicate (ID, DayInStudy) pairs are not supported")

    return df


def make_representation(
    *,
    subject_id: str,
    day: int,
    value: float,
    record_suffix: str,
) -> HistoricalRepresentation:
    start = BASE_DATE + timedelta(days=int(day) - 1)
    end = start + timedelta(days=1)

    status = (
        ObservationStatus.OBSERVED_ZERO
        if float(value) == 0.0
        else ObservationStatus.OBSERVED
    )

    return HistoricalRepresentation(
        representation_record_id=(
            f"mediaticino-{subject_id}-day-{day}-{record_suffix}"
        ),
        representation_spec_id=REPRESENTATION_SPEC_ID,
        subject_id=str(subject_id),
        phenomenon=PHENOMENON,
        interval_start=start,
        interval_end=end,
        value=float(value),
        unit=UNIT,
        status=status,
        coverage=Coverage(
            value=None,
            basis="distributed_artifact_daily_record",
        ),
        quality_flags=(),
        provenance=Provenance(
            source_id="MEDIATICINO_Dataset_LongFormat.csv",
            source_version=EXPECTED_SHA256,
            source_semantics=(
                "Daily total smartphone-on duration distributed by "
                "the source study; exact upstream within-day inference "
                "semantics remain outside F12-C."
            ),
            adapter_version="f12c_semisynthetic_v1",
        ),
        computed_at=end,
    )


def real_series_for_subject(
    subject_df: pd.DataFrame,
) -> list[HistoricalRepresentation]:
    records: list[HistoricalRepresentation] = []

    ordered = subject_df.sort_values("DayInStudy")

    for _, row in ordered.iterrows():
        value = pd.to_numeric(
            pd.Series([row[METRIC_COLUMN]]),
            errors="coerce",
        ).iloc[0]

        day = pd.to_numeric(
            pd.Series([row["DayInStudy"]]),
            errors="coerce",
        ).iloc[0]

        if pd.isna(value) or not np.isfinite(float(value)):
            continue
        if pd.isna(day):
            continue

        records.append(
            make_representation(
                subject_id=str(row["ID"]),
                day=int(day),
                value=float(value),
                record_suffix="real",
            )
        )

    return records


def run_arm(
    *,
    real_records: list[HistoricalRepresentation],
    start_index: int,
    shift_scale_multiplier: float,
    perturb: bool,
    config: C1DetectorConfig,
) -> dict:
    """
    Evaluate one paired arm.

    References for BOTH arms are always built from the same strictly prior
    REAL trajectory. Perturbed values never enter later references.

    The CUSUM state is arm-specific because accumulating detector evidence is
    precisely what F12-C is evaluating.
    """
    state = CusumState()
    outcomes = []
    first_change_offset = None

    end_index = min(
        len(real_records),
        start_index + PERTURBATION_LENGTH,
    )

    for idx in range(start_index, end_index):
        real_current = real_records[idx]
        real_history = real_records[:idx]

        reference = build_scalar_reference(
            real_current,
            real_history,
        )

        if (
            perturb
            and reference.estimable
            and reference.scale is not None
        ):
            value = (
                float(real_current.value)
                + shift_scale_multiplier * float(reference.scale)
            )
            current = make_representation(
                subject_id=real_current.subject_id,
                day=(
                    real_current.interval_start - BASE_DATE
                ).days
                + 1,
                value=value,
                record_suffix=(
                    f"shift-{shift_scale_multiplier:g}-offset-{idx-start_index}"
                ),
            )
        else:
            current = real_current

        result = evaluate_c1(
            current,
            reference,
            state,
            config,
            evaluation_id=(
                f"{real_current.subject_id}-"
                f"{start_index}-{idx}-"
                f"{'intervention' if perturb else 'control'}"
            ),
            analysis_version="f12c_semisynthetic_v1",
            computed_at=current.interval_end,
        )

        state = result.next_state
        evaluation = result.evaluation

        offset = idx - start_index

        if (
            first_change_offset is None
            and evaluation.outcome
            is DetectorEvaluationOutcome.CHANGE
        ):
            first_change_offset = offset

        outcomes.append(
            {
                "offset": offset,
                "day": (
                    current.interval_start - BASE_DATE
                ).days
                + 1,
                "outcome": evaluation.outcome.value,
                "statistic": evaluation.detector_statistic,
                "reference_location": evaluation.reference_location,
                "reference_scale": evaluation.reference_scale,
                "reference_history_count": (
                    evaluation.reference_history_count
                ),
            }
        )

    return {
        "first_change_offset": first_change_offset,
        "change_within_window": first_change_offset is not None,
        "final_positive_cusum": state.positive,
        "final_negative_cusum": state.negative,
        "evaluations": outcomes,
    }


def summarize_scenarios(scenarios: list[dict]) -> dict:
    if not scenarios:
        return {"n": 0}

    control_change = np.asarray(
        [s["control"]["change_within_window"] for s in scenarios],
        dtype=bool,
    )
    intervention_change = np.asarray(
        [s["intervention"]["change_within_window"] for s in scenarios],
        dtype=bool,
    )

    intervention_only = (~control_change) & intervention_change
    both = control_change & intervention_change
    neither = (~control_change) & (~intervention_change)
    control_only = control_change & (~intervention_change)

    delays = [
        s["intervention"]["first_change_offset"]
        for s in scenarios
        if s["intervention"]["first_change_offset"] is not None
    ]

    return {
        "n": len(scenarios),
        "control_change_rate": float(control_change.mean()),
        "intervention_change_rate": float(intervention_change.mean()),
        "paired_intervention_only_rate": float(intervention_only.mean()),
        "paired_both_change_rate": float(both.mean()),
        "paired_neither_change_rate": float(neither.mean()),
        "paired_control_only_rate": float(control_only.mean()),
        "intervention_first_change_offset": {
            "n": len(delays),
            "median": (
                float(np.median(delays))
                if delays
                else None
            ),
            "mean": (
                float(np.mean(delays))
                if delays
                else None
            ),
            "max": (
                int(max(delays))
                if delays
                else None
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "artifacts/f12/f12_c1_semisynthetic_duration.json"
        ),
    )
    args = parser.parse_args()

    df = load_dataset(args.csv)

    scenarios = []
    skipped_non_estimable_start = 0
    skipped_short_followup = 0

    for pid, group in df.groupby("ID", sort=False):
        records = real_series_for_subject(group)

        for start_index in range(len(records)):
            # F12-C1 requires exactly three observed continuation records.
            # Absent dataset rows are not imputed.
            if start_index + PERTURBATION_LENGTH > len(records):
                skipped_short_followup += 1
                continue

            current = records[start_index]
            history = records[:start_index]
            start_reference = build_scalar_reference(current, history)

            # This is experimental scenario admission, not a product
            # maturity rule.
            if start_reference.history_count < MIN_HISTORY:
                continue

            if not start_reference.estimable:
                skipped_non_estimable_start += 1
                continue

            for k in K_VALUES:
                for threshold in THRESHOLDS:
                    config = C1DetectorConfig(
                        k=k,
                        threshold=threshold,
                        min_history=MIN_HISTORY,
                    )

                    for shift in SHIFT_SCALES:
                        control = run_arm(
                            real_records=records,
                            start_index=start_index,
                            shift_scale_multiplier=shift,
                            perturb=False,
                            config=config,
                        )
                        intervention = run_arm(
                            real_records=records,
                            start_index=start_index,
                            shift_scale_multiplier=shift,
                            perturb=True,
                            config=config,
                        )

                        scenarios.append(
                            {
                                "subject_id": str(pid),
                                "start_day": (
                                    current.interval_start - BASE_DATE
                                ).days
                                + 1,
                                "history_count_at_start": (
                                    start_reference.history_count
                                ),
                                "reference_location_at_start": (
                                    start_reference.location
                                ),
                                "reference_scale_at_start": (
                                    start_reference.scale
                                ),
                                "k": k,
                                "threshold": threshold,
                                "min_history": MIN_HISTORY,
                                "shift_scale_multiplier": shift,
                                "perturbation_length": (
                                    PERTURBATION_LENGTH
                                ),
                                "control": control,
                                "intervention": intervention,
                            }
                        )

    grouped_summary = {}

    for k in K_VALUES:
        for threshold in THRESHOLDS:
            for shift in SHIFT_SCALES:
                key = (
                    f"k={k:g}|h={threshold:g}|"
                    f"shift={shift:g}scale"
                )
                subset = [
                    s
                    for s in scenarios
                    if s["k"] == k
                    and s["threshold"] == threshold
                    and s["shift_scale_multiplier"] == shift
                ]
                grouped_summary[key] = summarize_scenarios(subset)

    result = {
        "experiment": (
            "F12-C1 paired semisynthetic detector response "
            "on real human backgrounds"
        ),
        "dataset": {
            "file_name": args.csv.name,
            "sha256": sha256_file(args.csv),
            "rows": int(len(df)),
            "participants": int(df["ID"].nunique()),
        },
        "metric": {
            "column": METRIC_COLUMN,
            "phenomenon": PHENOMENON,
            "unit": UNIT,
        },
        "design": {
            "paired_control_intervention": True,
            "real_human_backgrounds": True,
            "reference_uses_real_prior_history_only": True,
            "perturbed_values_enter_future_reference": False,
            "missing_days_imputed": False,
            "perturbation_length_observed_records": PERTURBATION_LENGTH,
            "shift_scale_multipliers": list(SHIFT_SCALES),
            "k_values_experimental": list(K_VALUES),
            "thresholds_experimental": list(THRESHOLDS),
            "min_history_experimental": MIN_HISTORY,
            "product_parameter_selected": False,
            "real_ground_truth_available": False,
            "real_sensitivity_claimed": False,
            "real_specificity_claimed": False,
            "real_false_positive_rate_claimed": False,
            "detection_event_emission_evaluated": False,
            "reset_rearm_policy_evaluated": False,
        },
        "scenario_admission": {
            "requires_three_observed_continuation_records": True,
            "requires_estimable_start_reference": True,
            "skipped_non_estimable_start": skipped_non_estimable_start,
            "skipped_short_followup": skipped_short_followup,
        },
        "summary_by_experimental_condition": grouped_summary,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "experiment": result["experiment"],
                "dataset": result["dataset"],
                "metric": result["metric"],
                "design": result["design"],
                "scenario_admission": result["scenario_admission"],
                "scenario_count": result["scenario_count"],
                "summary_by_experimental_condition": grouped_summary,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nWROTE: {args.output}")


if __name__ == "__main__":
    main()
