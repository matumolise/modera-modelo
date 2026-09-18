import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PMU_FEATURES = [
    "age_scaled",
    "mean_daily_use_minutes",
    "mean_daily_session_count",
    "median_session_duration",
    "mean_daily_app_openings",
    "post_bedtime_use_ratio",
    "school_use_ratio",
    "games_share",
    "social_share",
    "entertainment_share",
    "education_share",
]

EXAMPLE_CHILD = {
    "age_scaled": 0.0,
    "mean_daily_use_minutes": 175.0,
    "mean_daily_session_count": 25.0,
    "median_session_duration": 4.5,
    "mean_daily_app_openings": 55.0,
    "post_bedtime_use_ratio": 0.11,
    "school_use_ratio": 0.06,
    "games_share": 0.20,
    "social_share": 0.20,
    "entertainment_share": 0.20,
    "education_share": 0.20,
}


def _run_python(script: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        raise AssertionError(
            "PMU isolation probe failed.\n"
            f"Interpreter: {sys.executable}\n"
            f"Exit code: {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError("PMU isolation probe produced no stdout")
    return lines[-1]


def _contract_probe(*, import_historical: bool) -> dict:
    historical_import = "import historical\n" if import_historical else ""
    script = f'''
import json
import config
from inference import build_input_dataframe
{historical_import}
example_child = {EXAMPLE_CHILD!r}
X = build_input_dataframe(example_child, list(config.DATASET_A_FEATURES))

missing = dict(example_child)
missing.pop("mean_daily_use_minutes")
missing_rejected = False
try:
    build_input_dataframe(missing, list(config.DATASET_A_FEATURES))
except ValueError:
    missing_rejected = True

invalid_ratio = dict(example_child)
invalid_ratio["school_use_ratio"] = 1.5
ratio_rejected = False
try:
    build_input_dataframe(invalid_ratio, list(config.DATASET_A_FEATURES))
except ValueError:
    ratio_rejected = True

print(json.dumps({{
    "features": list(config.DATASET_A_FEATURES),
    "columns": X.columns.tolist(),
    "values": [float(value) for value in X.iloc[0].tolist()],
    "missing_rejected": missing_rejected,
    "ratio_rejected": ratio_rejected,
}}, sort_keys=True))
'''
    return json.loads(_run_python(script))


def _prediction_probe(*, import_historical: bool) -> dict:
    historical_import = "import historical\n" if import_historical else ""
    script = f'''
import json
from inference import predict_pmu_severity
{historical_import}
example_child = {EXAMPLE_CHILD!r}
print(json.dumps(predict_pmu_severity(example_child), sort_keys=True))
'''
    return json.loads(_run_python(script))


class PMUIsolationTests(unittest.TestCase):
    def test_pmu_feature_contract_remains_the_existing_11_features(self) -> None:
        baseline = _contract_probe(import_historical=False)
        self.assertEqual(baseline["features"], EXPECTED_PMU_FEATURES)
        self.assertEqual(baseline["columns"], EXPECTED_PMU_FEATURES)

    def test_importing_historical_does_not_change_pmu_input_contract(self) -> None:
        baseline = _contract_probe(import_historical=False)
        with_historical = _contract_probe(import_historical=True)

        self.assertEqual(with_historical, baseline)
        self.assertTrue(baseline["missing_rejected"])
        self.assertTrue(baseline["ratio_rejected"])

    def test_historical_package_does_not_import_pmu_modules(self) -> None:
        script = '''
import json
import sys
import historical
print(json.dumps({
    "config_loaded": "config" in sys.modules,
    "inference_loaded": "inference" in sys.modules,
    "weekly_analysis_loaded": "weekly_analysis" in sys.modules,
}, sort_keys=True))
'''
        result = json.loads(_run_python(script))
        self.assertEqual(
            result,
            {
                "config_loaded": False,
                "inference_loaded": False,
                "weekly_analysis_loaded": False,
            },
        )

    def test_importing_historical_does_not_change_pmu_prediction(self) -> None:
        model_path = REPO_ROOT / "models" / "pmu_linear_v1.joblib"
        if not model_path.exists():
            self.skipTest("PMU model artifact is not present in this test workspace")

        baseline = _prediction_probe(import_historical=False)
        with_historical = _prediction_probe(import_historical=True)
        self.assertEqual(with_historical, baseline)


if __name__ == "__main__":
    unittest.main()
