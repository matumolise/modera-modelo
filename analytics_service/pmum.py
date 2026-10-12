"""Carga única y verificación técnica de PMUM v1, sin cambiar el estimador."""

import hashlib
import math
import threading
from numbers import Real

from .pmum_manifest import read_manifest, validate_manifest


class ModelUnavailable(RuntimeError):
    pass


class CachedPmum:
    def __init__(self, settings):
        self._lock = threading.Lock()
        self.ready = False
        try:
            import joblib
            from experiments.hu_pmum_candidate_v1 import EXPECTED_SHA256, FEATURES, MODEL_VERSION
            from experiments.hu_pmum_parent_adapter_v2 import estimate_with_predictor
            self.version = MODEL_VERSION
            self._estimate = estimate_with_predictor
            # Se verifica antes de deserializar: el hash esperado debe venir de una fuente confiable.
            digest = hashlib.sha256()
            with settings.model_path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
            if digest.hexdigest() != settings.model_sha256:
                raise ValueError("Huella del artefacto incompatible")
            manifest = validate_manifest(read_manifest(settings.manifest_path))
            # Cargar estos mismos bytes evita un cambio entre hash y joblib.load(path).
            import io
            raw = settings.model_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != settings.model_sha256:
                raise ValueError("El artefacto cambió durante la carga")
            artifact = joblib.load(io.BytesIO(raw))
            if not isinstance(artifact, dict) or not isinstance(manifest, dict):
                raise ValueError("Artefacto o manifiesto inválido")
            if not (manifest.get("model_version") == artifact.get("version") == MODEL_VERSION):
                raise ValueError("Versión incompatible")
            if not (manifest.get("source_sha256") == artifact.get("source_sha256") == EXPECTED_SHA256):
                raise ValueError("Fuente incompatible")
            if not (tuple(manifest.get("features", ())) == tuple(artifact.get("features", ())) == FEATURES):
                raise ValueError("Entradas incompatibles")
            if not (type(artifact.get("trained_rows")) is int
                    and manifest.get("n_trained") == artifact.get("trained_rows") == 803):
                raise ValueError("Cantidad de casos incompatible")
            sex_codes = artifact.get("sex_codes")
            if (not isinstance(sex_codes, list) or any(type(code) is not int for code in sex_codes)
                    or sex_codes != [1, 2] or artifact.get("target") != "PMUMTotal/9"):
                raise ValueError("Contrato del artefacto incompatible")
            self._model = artifact["model"]
            if not callable(getattr(self._model, "predict", None)):
                raise ValueError("Estimador ausente")
            self.ready = True
            reference = self._predict(9, 1, 2, 3)["estimated_pmum_sf_mean"]
            if abs(reference - 2.6959) > 0.0001:
                raise ValueError("Predicción de referencia incompatible")
        except Exception as exc:
            self.ready = False
            raise ModelUnavailable("No se pudo verificar el modelo") from exc

    def _predict(self, age, sex_code, weekday, weekend):
        from experiments.hu_pmum_candidate_v1 import row_for_model
        row = row_for_model(age, sex_code, weekday, weekend)
        with self._lock:
            if not self.ready:
                raise ModelUnavailable("Modelo no disponible")
            try:
                values = self._model.predict(row)
                if len(values) != 1:
                    raise ValueError("Cardinalidad de predicción inválida")
                if isinstance(values[0], bool) or not isinstance(values[0], Real):
                    raise ValueError("Prediccion requiere un escalar numerico real")
                value = float(values[0])
                if not math.isfinite(value):
                    raise ValueError("Predicción no finita")
            except Exception as exc:
                self.ready = False
                raise ModelUnavailable("Falló la inferencia") from exc
        return {
            "estimated_pmum_sf_mean": round(min(5.0, max(1.0, value)), 4),
            "model_version": self.version,
            "experimental": True,
        }

    def estimate(self, request):
        if not self.ready:
            raise ModelUnavailable("Modelo no disponible")
        return self._estimate(request, self._predict)
