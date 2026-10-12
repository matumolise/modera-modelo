"""Prepara un payload F12 sin enviarlo ni sobrescribir archivos existentes."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.f12_bridge import build_f12_request
from analytics_service.json_codec import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Entrada F12 excesiva")
        payload = build_f12_request(strict_json(args.input.read_bytes()))
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        print("PASS: payload preparado; conservarlo para enviar y reintentar. No se envio HTTP.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ImportError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
