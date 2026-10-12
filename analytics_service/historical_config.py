"""Perfil C1 obligatorio, versionado y sin umbrales predeterminados."""

import hashlib
import json
import math
import re
from dataclasses import dataclass

from historical.adapters import DAILY_USE_DURATION_SPEC_ID
from historical.detector import C1DetectorConfig

from .json_codec import strict_json

HISTORICAL_API_VERSION = "historical-http-v1-candidate"
REFERENCE_POLICY = "all_prior_usable_records_v1"
SCOPE = "internal_technical_candidate"


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise ValueError("Identificador invalido")
    return value


@dataclass(frozen=True)
class HistoricalProfile:
    configuration_id: str
    config: C1DetectorConfig
    analysis_version: str
    emitter_version: str

    @property
    def payload(self):
        return {
            "schema_version": 1, "configuration_id": self.configuration_id,
            "scope": SCOPE, "representation_spec_id": DAILY_USE_DURATION_SPEC_ID,
            "reference_policy": REFERENCE_POLICY,
            "analysis_version": self.analysis_version, "emitter_version": self.emitter_version,
            "detector": {"k": float(self.config.k), "threshold": float(self.config.threshold),
                         "min_history": self.config.min_history},
        }

    @property
    def fingerprint(self):
        raw = json.dumps(self.payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def binding(self):
        return {"historical_api_version": HISTORICAL_API_VERSION,
                "configuration": self.payload, "configuration_fingerprint": self.fingerprint}

    @classmethod
    def load(cls, path):
        if not path.is_file() or path.stat().st_size > 65536:
            raise ValueError("Perfil C1 ausente o excesivo")
        return cls.from_payload(strict_json(path.read_bytes()))

    @classmethod
    def from_payload(cls, value):
        keys = {"schema_version", "configuration_id", "scope", "representation_spec_id",
                "reference_policy", "analysis_version", "emitter_version", "detector"}
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError("Perfil C1 requiere todos los campos explicitos")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("Version del perfil incompatible")
        if (value["scope"] != SCOPE or value["reference_policy"] != REFERENCE_POLICY
                or value["representation_spec_id"] != DAILY_USE_DURATION_SPEC_ID):
            raise ValueError("Alcance, referencia o representacion no admitidos")
        detector = value["detector"]
        if not isinstance(detector, dict) or set(detector) != {"k", "threshold", "min_history"}:
            raise ValueError("Parametros C1 obligatorios")
        for key in ("k", "threshold"):
            number = detector[key]
            if type(number) not in (int, float) or not math.isfinite(float(number)):
                raise ValueError("Parametro C1 invalido: " + key)
        if type(detector["min_history"]) is not int:
            raise ValueError("min_history requiere entero")
        return cls(
            identifier(value["configuration_id"]),
            C1DetectorConfig(float(detector["k"]), float(detector["threshold"]), detector["min_history"]),
            identifier(value["analysis_version"]), identifier(value["emitter_version"]),
        )
