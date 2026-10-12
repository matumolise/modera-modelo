"""Audita un snapshot del repositorio C1; no escribe ni sustituye sus recibos."""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from analytics_service.historical_api import (
    BoundHistoricalRepository,
    parse_representation,
)
from analytics_service.historical_config import HistoricalProfile
from analytics_service.json_codec import strict_json
from historical.analyzer import analyze_c1_representation
from historical.persistence import deserialize_analyzer_state
from historical.receipts import deserialize_analysis_result


def audit_snapshot(repository_path, config_path):
    if repository_path.resolve() == config_path.resolve():
        raise ValueError("Rutas superpuestas")
    raw = repository_path.read_bytes()
    configuration = config_path.read_bytes()
    profile = HistoricalProfile.from_payload(strict_json(configuration))
    document = strict_json(raw)
    repository = BoundHistoricalRepository(repository_path, profile)
    repository._validate_document(document)
    histories = {}
    for value in document["representations"]:
        record = parse_representation(value)
        key = repository._stream_id(repository.stream_key(record))
        receipt = document["receipts"][record.representation_record_id]
        saved = deserialize_analysis_result(receipt["result"])
        previous = deserialize_analyzer_state(receipt["previous_state"])
        ev = saved.evaluation
        event = saved.emission.event
        rebuilt = analyze_c1_representation(
            record,
            histories.get(key, []),
            previous,
            profile.config,
            evaluation_id=ev.evaluation_id,
            event_id=event.event_id if event else ev.evaluation_id,
            analysis_version=profile.analysis_version,
            emitter_version=profile.emitter_version,
            computed_at=ev.computed_at,
            emitted_at=event.emitted_at if event else ev.computed_at,
        )
        if rebuilt != saved:
            raise ValueError("Recibo no corresponde a la historia previa de su serie")
        histories.setdefault(key, []).append(record)
    if repository_path.read_bytes() != raw or config_path.read_bytes() != configuration:
        raise ValueError(
            "Fuente modificada durante la auditoria; conservar snapshot estable"
        )
    return {
        "status": "PASS",
        "scope": "read_only_snapshot_reconstruction_not_calibration",
        "repository_sha256": sha256(raw).hexdigest(),
        "config_file_sha256": sha256(configuration).hexdigest(),
        "configuration_fingerprint": profile.fingerprint,
        "records": len(document["representations"]),
        "streams": len(histories),
        "reference_policy": "all_prior_usable_records_v1",
        "original_receipts_rewritten": False,
        "product_parameters_selected": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = audit_snapshot(a.repository, a.config)
        with a.output.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        print(
            "PASS: snapshot, referencias y recibos coherentes; originales sin cambios"
        )
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
