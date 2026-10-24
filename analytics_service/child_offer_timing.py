"""Espera operativa continua según PMUM-SF; no define cortes clínicos.

Los extremos son configuración explícita de ingeniería, no parámetros
aprendidos por Ridge ni intervalos validados con familias.
"""

from copy import deepcopy
import math
import re
from numbers import Real


TIMING_VERSION = "pmum-linear-cooldown-v1-engineering-candidate"
POLICY_VERSION = "automatic-child-offers-v2-pmum-engineering-candidate"


def adaptive_policy(base, minimum_minutes, maximum_minutes):
    # No reducir el mínimo operativo anterior de 120 minutos en este candidato.
    if (type(minimum_minutes) is not int or type(maximum_minutes) is not int
            or not 120 <= minimum_minutes < maximum_minutes <= 1440):
        raise ValueError("PMUM requiere 120 <= espera mínima < máxima <= 1440 minutos")
    policy = deepcopy(base)
    policy["legacy_cooldown_minutes"] = policy.pop("cooldown_minutes")
    policy.update(version=POLICY_VERSION, pmum_timing={
        "version": TIMING_VERSION,
        "minimum_minutes": minimum_minutes,
        "maximum_minutes": maximum_minutes,
        "missing_estimate": "suppress_automatic_offer",
        "freeze": "at_offer_generation_for_next_wait_after_confirmed_delivery",
    })
    return policy


def timing_from_estimate(result, configuration):
    if not isinstance(result, dict):
        raise ValueError("Resultado PMUM inválido")
    if result.get("status") == "unavailable":
        return {"status": "unavailable", "reason": result.get("reason", "pmum_unavailable")}
    from experiments.hu_pmum_candidate_v1 import MODEL_VERSION
    value = result.get("estimated_pmum_sf_mean")
    if (result.get("status") != "estimated" or result.get("model_version") != MODEL_VERSION
            or result.get("experimental") is not True or isinstance(value, bool)
            or not isinstance(value, Real) or not math.isfinite(value) or not 1 <= value <= 5
            or not isinstance(result.get("artifact_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", result["artifact_sha256"])):
        raise ValueError("Estimación PMUM incompatible con la espera")
    minimum, maximum = configuration["minimum_minutes"], configuration["maximum_minutes"]
    # Escala 1 -> espera máxima; escala 5 -> mínima. No hay clases de riesgo.
    minutes = maximum - (float(value) - 1.0) * (maximum - minimum) / 4.0
    return {
        "status": "estimated", "version": configuration["version"],
        "estimated_pmum_sf_mean": float(value), "model_version": MODEL_VERSION,
        "artifact_sha256": result["artifact_sha256"],
        "minimum_minutes": minimum, "maximum_minutes": maximum,
        "cooldown_minutes": minutes, "experimental": True,
    }
