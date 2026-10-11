"""Configuración explícita del candidato, independiente de parámetros C1."""

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    token: str
    host: str = "127.0.0.1"
    port: int = 8765
    pmum_enabled: bool = False
    activities_enabled: bool = True
    model_path: Path | None = None
    manifest_path: Path | None = None
    model_sha256: str | None = None
    body_timeout_seconds: float = 10.0
    max_body_bytes: int = 16384

    def __post_init__(self):
        if (not isinstance(self.token, str) or len(self.token) < 16
                or not self.token.isascii()
                or any(c.isspace() for c in self.token)):
            raise ValueError("ANALYTICS_SERVICE_TOKEN requiere 16+ caracteres ASCII sin espacios")
        if not self.host or type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Host o puerto inválido")
        if type(self.pmum_enabled) is not bool or type(self.activities_enabled) is not bool:
            raise ValueError("Las capacidades requieren valores booleanos")
        if (isinstance(self.body_timeout_seconds, bool)
                or not isinstance(self.body_timeout_seconds, (float, int))
                or not math.isfinite(self.body_timeout_seconds)
                or self.body_timeout_seconds <= 0):
            raise ValueError("Timeout de cuerpo inválido")
        if type(self.max_body_bytes) is not int or self.max_body_bytes <= 0:
            raise ValueError("Límite de cuerpo inválido")
        if self.pmum_enabled:
            if self.model_path is None or self.manifest_path is None:
                raise ValueError("PMUM requiere artefacto y manifiesto explícitos")
            if not re.fullmatch(r"[0-9a-f]{64}", self.model_sha256 or ""):
                raise ValueError("PMUM requiere SHA-256 esperado de origen confiable")

    @classmethod
    def from_env(cls):
        def boolean(name, default):
            value = os.environ.get(name, default).lower()
            if value not in {"true", "false"}:
                raise ValueError(name + " debe ser true o false")
            return value == "true"

        if boolean("ANALYTICS_HISTORICAL_ENABLED", "false"):
            raise ValueError("Histórico no implementado en este candidato")
        return cls(
            token=os.environ.get("ANALYTICS_SERVICE_TOKEN", ""),
            host=os.environ.get("ANALYTICS_HOST", "127.0.0.1"),
            port=int(os.environ.get("ANALYTICS_PORT", "8765")),
            pmum_enabled=boolean("ANALYTICS_PMUM_ENABLED", "false"),
            activities_enabled=boolean("ANALYTICS_ACTIVITIES_ENABLED", "true"),
            model_path=Path(os.environ["ANALYTICS_MODEL_PATH"])
                if os.environ.get("ANALYTICS_MODEL_PATH") else None,
            manifest_path=Path(os.environ["ANALYTICS_MODEL_MANIFEST_PATH"])
                if os.environ.get("ANALYTICS_MODEL_MANIFEST_PATH") else None,
            model_sha256=os.environ.get("ANALYTICS_MODEL_SHA256"),
            body_timeout_seconds=float(os.environ.get("ANALYTICS_REQUEST_TIMEOUT_SECONDS", "10")),
        )
