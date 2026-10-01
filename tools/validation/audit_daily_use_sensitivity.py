"""Auditoría reproducible de minutos sintéticos; no crea otro dataset.

Ejecutar desde cualquier directorio con:
    python tools/validation/audit_daily_use_sensitivity.py

Los escenarios modifican únicamente minutos diarios. No regeneran sesiones,
episodios, etiquetas PMU ni el Dataset A; sus salidas no sirven para inferencia.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from generate_behavior import add_daily_use_time, generate_daily_contexts  # noqa: E402
from generate_population import generate_population  # noqa: E402


def percentage(mask: np.ndarray) -> float:
    return round(float(mask.mean() * 100), 2)


def main() -> None:
    seeds = np.random.SeedSequence(config.CALIBRATION_SEED + 1).spawn(9)
    population = generate_population(config.N_CHILDREN_FINAL, seeds[0])
    contexts = generate_daily_contexts(population, seeds[1], config.N_DAYS)
    days = add_daily_use_time(contexts, population, np.random.default_rng(seeds[2]))

    expected = pd.read_csv(ROOT / "data/final/dataset_a_recreated.csv")
    actual_weekly = days.groupby("child_id").daily_use_minutes.mean()
    expected_weekly = expected.set_index("child_id").mean_daily_use_minutes
    max_difference = float((actual_weekly - expected_weekly).abs().max())
    if not np.isfinite(max_difference) or max_difference > 1e-9:
        raise RuntimeError(f"Los días no reproducen el CSV: {max_difference}")

    baseline = days.daily_use_minutes.to_numpy()
    weekday_6_11 = (~days.is_weekend.to_numpy()) & (days.age_scaled.to_numpy() < 1.5)
    rng = np.random.default_rng(20261001)
    zero_draws = rng.random(len(days))
    variation_draws = rng.standard_normal(len(days))
    scenarios = [
        ("base", 0.0, 0.0),
        ("zero_05", 0.05, 0.0),
        ("zero_15", 0.15, 0.0),
        ("variation_025", 0.0, 0.25),
        ("zero_05_variation_025", 0.05, 0.25),
        ("zero_15_variation_025", 0.15, 0.25),
    ]
    results = []
    for name, zero_probability, extra_log_sigma in scenarios:
        values = baseline * np.exp(
            extra_log_sigma * variation_draws - extra_log_sigma**2 / 2
        )
        values = values.copy()
        values[zero_draws < zero_probability] = 0.0
        selected = values[weekday_6_11]
        results.append(
            {
                "scenario": name,
                "zero_probability_assumed": zero_probability,
                "extra_log_sigma_assumed": extra_log_sigma,
                "zero_days_all_ages": int((values == 0).sum()),
                "all_days_mean_minutes": round(float(values.mean()), 2),
                "weekdays_6_11_n": int(len(selected)),
                "weekdays_6_11_percent_lt_1h": percentage(selected < 60),
                "weekdays_6_11_percent_1_to_lt_2h": percentage(
                    (selected >= 60) & (selected < 120)
                ),
                "weekdays_6_11_percent_2_to_lt_4h": percentage(
                    (selected >= 120) & (selected < 240)
                ),
                "weekdays_6_11_percent_4_to_lt_6h": percentage(
                    (selected >= 240) & (selected < 360)
                ),
                "weekdays_6_11_percent_ge_6h": percentage(selected >= 360),
            }
        )

    print(json.dumps({"base_n_days": len(days), "max_weekly_csv_difference": max_difference,
                      "scenarios": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
