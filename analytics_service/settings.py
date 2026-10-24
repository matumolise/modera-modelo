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
    historical_enabled: bool = False
    historical_repository_path: Path | None = None
    historical_config_path: Path | None = None
    adult_messages_enabled: bool = False
    adult_messages_repository_path: Path | None = None
    child_offers_enabled: bool = False
    child_offers_repository_path: Path | None = None
    child_offers_pmum_min_minutes: int | None = None
    child_offers_pmum_max_minutes: int | None = None

    def __post_init__(self):
        if (not isinstance(self.token, str) or len(self.token) < 16
                or not self.token.isascii()
                or any(c.isspace() for c in self.token)):
            raise ValueError("ANALYTICS_SERVICE_TOKEN requiere 16+ caracteres ASCII sin espacios")
        if not self.host or type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Host o puerto inválido")
        if any(type(value) is not bool for value in
               (self.pmum_enabled, self.activities_enabled, self.historical_enabled,
                self.adult_messages_enabled, self.child_offers_enabled)):
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
        if self.historical_enabled:
            if any(not isinstance(path, Path) or not path.is_absolute() for path in
                   (self.historical_repository_path, self.historical_config_path)):
                raise ValueError("Historico requiere rutas absolutas de perfil y repositorio")
        if self.adult_messages_enabled:
            if not isinstance(self.adult_messages_repository_path, Path) or not self.adult_messages_repository_path.is_absolute():
                raise ValueError("Mensajes adultos requieren una base absoluta independiente de C1")
            if (self.historical_repository_path is not None
                    and self.adult_messages_repository_path.resolve() == self.historical_repository_path.resolve()):
                raise ValueError("Mensajes adultos y C1 requieren repositorios diferentes")
        if self.child_offers_enabled:
            path = self.child_offers_repository_path
            if not isinstance(path, Path) or not path.is_absolute():
                raise ValueError("El coordinador requiere una base absoluta inicializada")
            for other in (self.historical_repository_path, self.adult_messages_repository_path,
                          self.historical_config_path, self.model_path, self.manifest_path):
                if other is not None and path.resolve() == other.resolve():
                    raise ValueError("El coordinador requiere una base independiente")
        if self.child_offers_pmum_min_minutes is not None or self.child_offers_pmum_max_minutes is not None:
            from .child_offers import POLICY
            from .child_offer_timing import adaptive_policy
            if not self.pmum_enabled or not self.child_offers_enabled:
                raise ValueError("La adaptación requiere PMUM y coordinador habilitados")
            adaptive_policy(POLICY, self.child_offers_pmum_min_minutes,
                            self.child_offers_pmum_max_minutes)

    def child_offer_policy(self):
        from .child_offers import POLICY
        from .child_offer_timing import adaptive_policy
        if self.child_offers_pmum_min_minutes is None:
            return POLICY
        return adaptive_policy(POLICY, self.child_offers_pmum_min_minutes,
                               self.child_offers_pmum_max_minutes)

    @classmethod
    def from_env(cls):
        def boolean(name, default):
            value = os.environ.get(name, default).lower()
            if value not in {"true", "false"}:
                raise ValueError(name + " debe ser true o false")
            return value == "true"

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
            historical_enabled=boolean("ANALYTICS_HISTORICAL_ENABLED", "false"),
            historical_repository_path=Path(os.environ["ANALYTICS_HISTORICAL_REPOSITORY_PATH"])
                if os.environ.get("ANALYTICS_HISTORICAL_REPOSITORY_PATH") else None,
            historical_config_path=Path(os.environ["ANALYTICS_HISTORICAL_CONFIG_PATH"])
                if os.environ.get("ANALYTICS_HISTORICAL_CONFIG_PATH") else None,
            adult_messages_enabled=boolean("ANALYTICS_ADULT_MESSAGES_ENABLED", "false"),
            adult_messages_repository_path=Path(os.environ["ANALYTICS_ADULT_MESSAGES_REPOSITORY_PATH"])
                if os.environ.get("ANALYTICS_ADULT_MESSAGES_REPOSITORY_PATH") else None,
            child_offers_enabled=boolean("ANALYTICS_CHILD_OFFERS_ENABLED", "false"),
            child_offers_repository_path=Path(os.environ["ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH"])
                if os.environ.get("ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH") else None,
            child_offers_pmum_min_minutes=int(os.environ["ANALYTICS_CHILD_OFFERS_PMUM_MIN_MINUTES"])
                if os.environ.get("ANALYTICS_CHILD_OFFERS_PMUM_MIN_MINUTES") else None,
            child_offers_pmum_max_minutes=int(os.environ["ANALYTICS_CHILD_OFFERS_PMUM_MAX_MINUTES"])
                if os.environ.get("ANALYTICS_CHILD_OFFERS_PMUM_MAX_MINUTES") else None,
        )
