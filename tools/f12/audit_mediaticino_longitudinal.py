from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_SHA256 = (
    "cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e"
)

REQUIRED_COLUMNS = {
    "ID",
    "DayInStudy",
    "totTurnONPerDay",
    "totOnDurPerDayMin",
    "OUTLIERS",
    "SD",
}

METRICS = {
    "duration_minutes": "totOnDurPerDayMin",
    "turn_on_count": "totTurnONPerDay",
}

HISTORY_CHECKPOINTS = (1, 3, 7, 14, 28)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def q(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {"n": 0}
    return {
        "n": int(x.size),
        "min": float(x.min()),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "mean": float(x.mean()),
        "p75": float(x.quantile(0.75)),
        "max": float(x.max()),
    }


def participant_temporal_summary(df: pd.DataFrame) -> dict:
    rows = []

    for pid, g in df.groupby("ID", sort=False):
        days = sorted(pd.to_numeric(g["DayInStudy"], errors="coerce").dropna().astype(int).unique())

        if not days:
            continue

        first_day = days[0]
        last_day = days[-1]
        span = last_day - first_day + 1
        observed = len(days)
        missing_inside_span = span - observed

        rows.append(
            {
                "ID": pid,
                "observed_days": observed,
                "first_day": first_day,
                "last_day": last_day,
                "span_days": span,
                "missing_inside_span": missing_inside_span,
                "span_coverage": observed / span if span else np.nan,
            }
        )

    p = pd.DataFrame(rows)

    return {
        "participants": int(len(p)),
        "observed_days_per_participant": q(p["observed_days"]),
        "span_days_per_participant": q(p["span_days"]),
        "span_coverage": q(p["span_coverage"]),
        "participants_with_internal_gaps": int((p["missing_inside_span"] > 0).sum()),
        "participants_without_internal_gaps": int((p["missing_inside_span"] == 0).sum()),
    }


def within_person_variation(df: pd.DataFrame, column: str) -> dict:
    per_person = []

    for _, g in df.groupby("ID", sort=False):
        x = pd.to_numeric(g[column], errors="coerce").dropna()

        if x.empty:
            continue

        med = float(x.median())
        mad = float((x - med).abs().median())

        per_person.append(
            {
                "n": int(x.size),
                "sd": float(x.std(ddof=1)) if x.size > 1 else np.nan,
                "range": float(x.max() - x.min()),
                "full_history_mad": mad,
            }
        )

    p = pd.DataFrame(per_person)

    return {
        "participants_with_values": int(len(p)),
        "within_person_sd": q(p["sd"]),
        "within_person_range": q(p["range"]),
        "full_history_mad": q(p["full_history_mad"]),
        "participants_full_history_mad_zero": int((p["full_history_mad"] == 0).sum()),
    }


def prequential_reference_audit(df: pd.DataFrame, column: str) -> dict:
    """
    Audit history-only median/MAD availability.

    Current row x_t is NEVER included in its own reference.
    No detector threshold or maturity policy is selected here.
    """
    records = []

    for pid, g in df.groupby("ID", sort=False):
        g = g.sort_values("DayInStudy")
        history: list[float] = []

        for _, row in g.iterrows():
            value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]

            finite_history = np.asarray(history, dtype=float)
            finite_history = finite_history[np.isfinite(finite_history)]

            if finite_history.size:
                median = float(np.median(finite_history))
                mad = float(np.median(np.abs(finite_history - median)))
                scale = 1.4826 * mad
            else:
                mad = np.nan
                scale = np.nan

            records.append(
                {
                    "ID": pid,
                    "DayInStudy": row["DayInStudy"],
                    "history_n": int(finite_history.size),
                    "positive_finite_scale": bool(
                        np.isfinite(scale) and scale > 0
                    ),
                    "mad_zero": bool(
                        finite_history.size > 0
                        and np.isfinite(mad)
                        and mad == 0
                    ),
                }
            )

            if pd.notna(value) and np.isfinite(float(value)):
                history.append(float(value))

    r = pd.DataFrame(records)

    checkpoints = {}
    for n in HISTORY_CHECKPOINTS:
        eligible = r[r["history_n"] >= n]
        checkpoints[str(n)] = {
            "rows_with_at_least_n_prior_values": int(len(eligible)),
            "participants_reaching_n_prior_values": int(
                eligible["ID"].nunique()
            ),
            "rows_with_positive_finite_mad_scale": int(
                eligible["positive_finite_scale"].sum()
            ),
            "positive_scale_rate_given_history": (
                float(eligible["positive_finite_scale"].mean())
                if len(eligible)
                else None
            ),
        }

    return {
        "evaluated_rows": int(len(r)),
        "rows_with_no_prior_history": int((r["history_n"] == 0).sum()),
        "rows_with_any_prior_history": int((r["history_n"] > 0).sum()),
        "rows_with_positive_finite_mad_scale": int(
            r["positive_finite_scale"].sum()
        ),
        "rows_with_zero_mad_given_history": int(
            ((r["history_n"] > 0) & r["mad_zero"]).sum()
        ),
        "history_checkpoints_descriptive_only": checkpoints,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/f12/f12_b2_mediaticino_audit.json"),
    )
    args = parser.parse_args()

    actual_hash = sha256_file(args.csv)

    if actual_hash.lower() != EXPECTED_SHA256:
        raise SystemExit(
            f"Unexpected dataset SHA256: {actual_hash}"
        )

    df = pd.read_csv(args.csv, na_values=["-99"])

    # The distributed artifact contains at least one column name with
    # surrounding whitespace (e.g. " totOnDurPerDayMin ").
    # Normalize header whitespace only; raw data values are not altered.
    original_columns = list(df.columns)
    normalized_columns = [str(c).strip() for c in original_columns]

    if len(normalized_columns) != len(set(normalized_columns)):
        raise SystemExit(
            "Column-name normalization would create duplicate columns"
        )

    df.columns = normalized_columns

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise SystemExit(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    duplicate_pairs = int(df.duplicated(["ID", "DayInStudy"]).sum())

    def audit_cohort(cohort: pd.DataFrame) -> dict:
        cohort_result = {
            "rows": int(len(cohort)),
            "participants": int(cohort["ID"].nunique()),
            "temporal_structure": participant_temporal_summary(cohort),
            "metrics": {},
        }

        for label, column in METRICS.items():
            numeric = pd.to_numeric(cohort[column], errors="coerce")

            cohort_result["metrics"][label] = {
                "column": column,
                "observed_values": q(numeric),
                "zero_value_rows": int((numeric == 0).sum()),
                "missing_value_rows": int(numeric.isna().sum()),
                "within_person_variation": within_person_variation(
                    cohort, column
                ),
                "prequential_reference": prequential_reference_audit(
                    cohort, column
                ),
            }

        return cohort_result

    # Reconstruct the subset used by the published analysis.
    # These are source-study filters, NOT Moderá eligibility rules.
    published_subset = df[
        (pd.to_numeric(df["OUTLIERS"], errors="coerce") == 1)
        & (pd.to_numeric(df["SD"], errors="coerce") == 1)
    ].copy()

    result = {
        "experiment": "F12-B2 real human trajectory descriptive audit",
        "dataset": {
            "file_name": args.csv.name,
            "sha256": actual_hash,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "participants": int(df["ID"].nunique()),
            "duplicate_id_day_pairs": duplicate_pairs,
        },
        "scope": {
            "cusum_executed": False,
            "threshold_selected": False,
            "maturity_selected": False,
            "missing_days_imputed": False,
            "day1_automatically_excluded": False,
            "published_filters_used_as_modera_rules": False,
        },
        "cohorts": {
            "distributed_artifact": {
                "definition": "All rows distributed in the inspected CSV.",
                "audit": audit_cohort(df),
            },
            "published_filter_subset": {
                "definition": (
                    "Rows belonging to participants satisfying "
                    "OUTLIERS == 1 and SD == 1, reconstructed only for "
                    "comparison with the source study."
                ),
                "audit": audit_cohort(published_subset),
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nWROTE: {args.output}")


if __name__ == "__main__":
    main()


