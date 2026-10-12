"""JSON UTF-8 estricto para transporte y archivos del candidato."""

import json
import math


def strict_json(body):
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("JSON no finito")
        return result

    def constant(_):
        raise ValueError("JSON no finito")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Clave duplicada")
            result[key] = value
        return result

    return json.loads(body.decode("utf-8"), parse_constant=constant,
                      parse_float=finite_float, object_pairs_hook=pairs)
