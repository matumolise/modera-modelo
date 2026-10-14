"""Read-only provenance reconciliation. Never fits, predicts or loads joblib.

Reads the registered source and a historical evaluation package. The artifact
check is a transcription of the user's Windows result, not a new local run.
pyreadstat is an optional dependency only for source metadata inspection.
"""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from sklearn.model_selection import KFold
from experiments.hu_pmum_real_data import load_hungarian, names_from_input
from tools.validation.verify_pmum_artifact_v1 import EXPECTED_ARTIFACT_SHA256

SOURCE_SHA = "f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5"
MANIFEST_SHA = "98f2952c2bf0c2e4565fe86cadd0fe28faeae4ef4600a0d36c09983779495b09"
PACKAGE_SHA = "544ac6a5f4d2906454c772ad48b30cf16c28ccabe2798da89d82efee00ede539"
REPORT_SHA = "f0eb942342857259651dc17ae7d728689eb75329cc3b1403df2f59352e1630f9"
ORIGINAL_COMMIT = "d597ce7c02151cefad4f2c36e3badd7c1e1b621f"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def index_hash(indices):
    return digest(np.asarray(indices, dtype="<i8").tobytes())


def function_ast(text, name):
    return ast.dump(next(node for node in ast.parse(text).body
                         if isinstance(node, ast.FunctionDef) and node.name == name),
                    include_attributes=False)


def audit(source, package, manifest_path, check_path):
    import pyreadstat
    source_bytes = source.read_bytes()
    require(digest(source_bytes) == SOURCE_SHA, "Source ZIP hash mismatch")
    require(digest(package.read_bytes()) == PACKAGE_SHA, "Historical package hash mismatch")
    manifest_bytes = manifest_path.read_bytes()
    require(digest(manifest_bytes) == MANIFEST_SHA, "Recovered original manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    check = json.loads(check_path.read_text(encoding="utf-8"))["reported_result"]
    require(check["status"] == "PASS" and check["artifact_sha256"] == EXPECTED_ARTIFACT_SHA256
            and check["manifest_sha256"] == MANIFEST_SHA and check["original_files_unchanged"] is True
            and check["new_model_trained"] is False and check["grid_cases"] == 350
            and check["fractional_age_checks"] == 2,
            "Reported Windows check does not match the registered originals")
    with zipfile.ZipFile(package) as archive:
        name = next(n for n in archive.namelist() if n.endswith("/PMUM_OOF_HIGH_REAUDIT.json"))
        report_bytes = archive.read(name)
    require(digest(report_bytes) == REPORT_SHA, "Historical evaluation report hash mismatch")
    report = json.loads(report_bytes)
    require(report["source_sha256"] == SOURCE_SHA, "Evaluation uses another source")
    x, y, _ = load_hungarian(source)
    indices = np.flatnonzero(np.isin(x[:, 1], ["1", "2"]))
    require(len(x) == 806 and len(indices) == 803, "Cohort mismatch")
    require(report["source_index_order_sha256"] == index_hash(indices), "Cohort order mismatch")
    fold_checks = []
    for number, (train, test) in enumerate(KFold(5, shuffle=True, random_state=1027).split(indices)):
        recorded = report["folds"][number]
        require(recorded["train_source_indices_sha256"] == index_hash(indices[train])
                and recorded["test_source_indices_sha256"] == index_hash(indices[test]),
                "Historical fold indices mismatch")
        alpha = min((score, int(key)) for key, score in recorded["inner_unclipped_cv_mae"].items())[1]
        require(alpha == recorded["selected_alpha"], "Recorded alpha inconsistent with saved scores")
        fold_checks.append({"fold": number, "n_train": len(train), "n_test": len(test), "alpha": alpha})
    with zipfile.ZipFile(source) as archive, TemporaryDirectory() as directory:
        names = names_from_input(archive.read("SEM.inp").decode("utf-8-sig"))
        frames, metadata, entry_hashes = {}, {}, {}
        for name in ("SEM.sav", "CFA.sav"):
            data = archive.read(name)
            entry_hashes[name] = digest(data)
            path = Path(directory) / name
            path.write_bytes(data)
            frames[name], metadata[name] = pyreadstat.read_sav(path, user_missing=True)
        sem, cfa = frames["SEM.sav"], frames["CFA.sav"]
        meta = metadata["SEM.sav"]
        require(len(sem) == 2514 and len(cfa) == 2514
                and sem["ID"].is_unique and cfa["ID"].is_unique, "Source ID linkage is ambiguous")
        column = lambda name: meta.column_names[names.index(name)]
        complete = (sem["filter"] == 1) & sem[column("CHAge")].between(6, 12)
        for i in range(1, 10):
            values = sem[column("PMUM" + str(i))]
            complete &= values.between(1, 5) & (values % 1 == 0)
        require(int(complete.sum()) == 806, "SAV completeness mismatch")
        cohort = complete & sem[column("CHGender")].isin([1, 2])
        require(int(cohort.sum()) == 803, "SAV operational cohort mismatch")
        observed = sem.loc[cohort]
        require(np.array_equal(observed[column("PMUMTotal")].to_numpy() / 9, y[indices]),
                "SAV target differs from loader target")
        expected = np.empty((len(observed), 4), dtype=object)
        expected[:, 0] = observed[column("CHAge")].to_numpy()
        for i, field in enumerate(("CHGender", "STIWeekday", "STIWeekend"), start=1):
            expected[:, i] = observed[column(field)].map(lambda v: str(int(v))).to_numpy()
        require(np.array_equal(expected, x[indices]), "SAV predictors differ from loader predictors")
        joined = sem.merge(cfa[["ID", "GyerekekSzáma", "GyerekekSzáma_3KAT"]],
                           on="ID", how="left", suffixes=("", "_cfa"), validate="one_to_one")
        recode = column("NoChildren")
        a, b = joined[recode], joined[recode + "_cfa"]
        require(bool((a.eq(b) | (a.isna() & b.isna())).all()), "SEM/CFA recodings differ")
        require(bool((a.eq(1) == joined["GyerekekSzáma"].eq(1)).all()), "Code 1 recoding mismatch")
        require(int(sem.loc[cohort, recode].eq(1).sum()) == 300, "Subgroup count mismatch")
        question = {}
        for field in ("STIWeekday", "STIWeekend", "CHGender"):
            col = column(field)
            question[field] = {"sav_column": col, "label": meta.column_names_to_labels[col],
                               "value_labels": meta.variable_value_labels.get(col)}
        question["NoChildren"] = {
            "sav_column": recode, "raw_count_column_in_CFA": "GyerekekSzáma",
            "raw_count_question": metadata["CFA.sav"].column_names_to_labels["GyerekekSzáma"],
            "code_1_equivalent_to_raw_count_1_all_rows": True, "subgroup_n": 300,
            "household_or_informant_independence_proven": False,
        }
    old_source = subprocess.check_output(["git", "show", ORIGINAL_COMMIT + ":experiments/hu_pmum_candidate_v1.py"],
                                         cwd=ROOT).decode("utf-8")
    current_source = (ROOT / "experiments/hu_pmum_candidate_v1.py").read_text(encoding="utf-8")
    old_loader = subprocess.check_output(["git", "show", ORIGINAL_COMMIT + ":experiments/hu_pmum_real_data.py"],
                                         cwd=ROOT).decode("utf-8")
    current_loader = (ROOT / "experiments/hu_pmum_real_data.py").read_text(encoding="utf-8")
    require(function_ast(old_source, "train") == function_ast(current_source, "train"), "Train function changed")
    require(old_loader == current_loader, "Original loader/transformers changed")
    errors = {}
    for name in ("fixed_alpha_1", "nested_selection"):
        fraction = report["error_diagnostics"][name]["fraction_error_over_one_scale_point"]
        count = round(fraction * 803)
        require(abs(fraction - count / 803) < 1e-12, "Error fraction denominator mismatch")
        errors[name] = {"n": 803, "error_over_one_count": count, "percent": 100 * fraction}
    return {
        "status": "PASS", "scope": "read_only_provenance_reconciliation_not_new_training_or_external_validation",
        "source_sha256": SOURCE_SHA, "source_entry_sha256": entry_hashes,
        "evaluation_package_sha256": PACKAGE_SHA, "historical_report_sha256": REPORT_SHA,
        "original_artifact_sha256_reported_in_windows": EXPECTED_ARTIFACT_SHA256,
        "manifest_recovered_bytes_sha256": MANIFEST_SHA,
        "manifest_recovery": "user_Get_Content_text_serialized_as_original_CRLF_hash_identical",
        "manifest_created_utc": manifest["created_utc"], "original_files_modified": False,
        "artifact_loaded_here": False, "fit_executed": False, "new_predictions_computed": False,
        "metrics": report["metrics"]["all"], "error_attribution": errors,
        "fold_checks": fold_checks, "questions_and_recoding": question,
        "source_cohort_n": 803, "original_train_function_AST_unchanged": True,
        "original_loader_text_unchanged": True,
        "earliest_available_committed_snapshot": ORIGINAL_COMMIT,
        "exact_pre_training_snapshot_proven": False,
        "raw_OOF_vectors_in_historical_report": False,
        "source_metadata_reader": "pyreadstat " + pyreadstat.__version__,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--evaluation-package", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reported-check", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source_zip, args.evaluation_package, args.manifest, args.reported_check)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, allow_nan=False, indent=2)
        output.write("\n")
    print("PASS: source, historical folds, error attribution and provenance; no fit or artifact load")


if __name__ == "__main__":
    main()
