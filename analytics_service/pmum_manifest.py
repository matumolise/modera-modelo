"""Contrato del manifiesto HU v1; no modifica artefactos ni valida su eficacia."""

from datetime import datetime, timezone

from .json_codec import strict_json

MANIFEST_TARGET = "PMUM-SF mean, 1 to 5"
MANIFEST_SOURCE = "Zenodo 21802447 / SEM.dat"
MANIFEST_STATUS = "NOT APPROVED; no app integration"
MAX_MANIFEST_BYTES = 65536


def read_manifest(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Manifiesto excesivo")
    return strict_json(raw)


def validate_manifest(manifest):
    from experiments.hu_pmum_candidate_v1 import (
        EXPECTED_SHA256,
        FEATURES,
        MODEL_VERSION,
    )

    required = {
        "model_version",
        "source",
        "source_sha256",
        "created_utc",
        "features",
        "target",
        "n_trained",
        "sex_code_4_excluded",
        "regularization",
        "evaluation",
        "deployment_status",
    }
    if not isinstance(manifest, dict) or not required <= set(manifest):
        raise ValueError("Manifiesto HU v1 incompleto")
    if (
        manifest["model_version"] != MODEL_VERSION
        or manifest["source"] != MANIFEST_SOURCE
        or manifest["source_sha256"] != EXPECTED_SHA256
        or manifest["target"] != MANIFEST_TARGET
        or manifest["deployment_status"] != MANIFEST_STATUS
    ):
        raise ValueError(
            "Version, fuente, escala o alcance del manifiesto incompatibles"
        )
    if (
        not isinstance(manifest["features"], list)
        or tuple(manifest["features"]) != FEATURES
        or type(manifest["n_trained"]) is not int
        or manifest["n_trained"] != 803
        or type(manifest["sex_code_4_excluded"]) is not int
        or manifest["sex_code_4_excluded"] != 3
    ):
        raise ValueError("Entradas o conteos del manifiesto incompatibles")
    for key in ("regularization", "evaluation"):
        if (
            not isinstance(manifest[key], str)
            or not manifest[key].strip()
            or len(manifest[key]) > 2048
        ):
            raise ValueError("Descripcion del entrenamiento/evaluacion ausente")
    created = manifest["created_utc"]
    if not isinstance(created, str) or len(created) > 64:
        raise ValueError("Fecha del manifiesto incompatible")
    parsed = datetime.fromisoformat(
        created[:-1] + "+00:00" if created.endswith("Z") else created
    )
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("created_utc requiere zona UTC")
    # La descripcion de evaluacion se conserva como metadata histórica;
    # no prueba que cada métrica corresponda al estimador fijo alpha=1.
    return manifest
