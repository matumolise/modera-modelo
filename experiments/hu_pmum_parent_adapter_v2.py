"""Contrato interno de integración del PMUM-SF experimental, sin HTTP.

No usar como evaluación clínica ni publicar una estimación a familias sin
resolver alcance docente, formulario y validación externa.
"""

from pathlib import Path

from hu_pmum_candidate_v1 import predict, row_for_model


REQUIRED = frozenset({"age", "sex_code", "weekday_category",
                      "weekend_category", "respondent", "reference_days"})


def estimate(model_path: str | Path, request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "unavailable", "reason": "invalid_request"}
    if set(request) - REQUIRED:
        return {"status": "unavailable", "reason": "unexpected_field"}
    if request.get("weekday_category") is None or request.get("weekend_category") is None:
        return {"status": "unavailable", "reason": "missing_parent_answer"}
    if set(request) != REQUIRED:
        return {"status": "unavailable", "reason": "missing_required_field"}
    if request["respondent"] != "parent_or_caregiver":
        return {"status": "unavailable", "reason": "respondent_mismatch"}
    if type(request["reference_days"]) is not int or request["reference_days"] != 30:
        return {"status": "unavailable", "reason": "reference_period_mismatch"}
    try:
        row_for_model(request["age"], request["sex_code"],
                      request["weekday_category"], request["weekend_category"])
    except ValueError:
        return {"status": "unavailable", "reason": "invalid_feature_value"}
    result = predict(model_path, request["age"], request["sex_code"],
                     request["weekday_category"], request["weekend_category"])
    # Archivo ausente o corrupto, o versión de modelo incompatible, debe
    # propagarse como error técnico; no se debe disfrazar como respuesta omitida.
    return {"status": "estimated", "estimated_pmum_sf_mean": result["estimated_pmum_sf_mean"],
            "model_version": result["model_version"], "experimental": True,
            "use": "internal_research_only"}
