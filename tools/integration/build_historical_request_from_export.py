"""Archiva exports originales y prepara un día cerrado sin enviar HTTP."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_service.f12_export import MAX_BYTES, prepare_android_export
from analytics_service.json_codec import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", type=Path, nargs=2, action="append",
                        metavar=("SUMMARY_JSON", "EVENTS_JSONL"))
    source.add_argument("--no-export", action="store_true",
                        help="Declaracion explicita del backend: sin archivos; produce MISSING")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    created = False
    try:
        paths = [args.binding] + [path for pair in (args.run or []) for path in pair]
        if sum(path.stat().st_size for path in paths) > MAX_BYTES:
            raise ValueError("Entrada excesiva")
        binding_bytes = args.binding.read_bytes()
        pairs = [(summary.read_bytes(), events.read_bytes()) for summary, events in (args.run or [])]
        if len(binding_bytes) > 65536 or len(binding_bytes) + sum(len(s) + len(e) for s, e in pairs) > MAX_BYTES:
            raise ValueError("Entrada leida excesiva")
        result = prepare_android_export(strict_json(binding_bytes), pairs)
        # Validar todo antes de crear; mkdir exclusivo, sin borrar preexistentes.
        args.output_dir.mkdir(parents=False, exist_ok=False)
        created = True
        (args.output_dir / "binding.original.json").write_bytes(binding_bytes)
        for pair, row in zip(pairs, result["preparation"]["summaries"]):
            original = args.output_dir / "originals" / row["collector_run_id"]
            original.mkdir(parents=True)
            (original / "summary.json").write_bytes(pair[0])
            (original / "events.jsonl").write_bytes(pair[1])
        for name, value in (("preparation.json", result["preparation"]),
                            ("request.json", result["request"]), ("lineage.json", result["audit"])):
            (args.output_dir / name).write_text(json.dumps(value, ensure_ascii=False,
                                                         allow_nan=False, indent=2) + "\n", encoding="utf-8")
        files = sorted(path for path in args.output_dir.rglob("*") if path.is_file())
        checksums = "".join(sha256(path.read_bytes()).hexdigest() + "  "
                            + path.relative_to(args.output_dir).as_posix() + "\n" for path in files)
        (args.output_dir / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
        print("PASS: " + ("sin export declarado; MISSING preparado" if args.no_export
                           else "originales archivados; request.json preparado") + ". No se envio HTTP.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ImportError) as exc:
        if created:
            shutil.rmtree(args.output_dir)
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
