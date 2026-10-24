"""Copia una base v1 a otra ruta y habilita PMUM sin borrar historial ni recibos.

Detener primero el servicio para efectuar el corte. La base original se conserva
sin modificar. La ruta de destino debe ser nueva.
"""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .child_offers import ChildOfferCoordinator, POLICY, _json, _stored_state
from .child_offer_timing import adaptive_policy


def migrate(source, target, minimum_minutes, maximum_minutes):
    source, target = Path(source), Path(target)
    if not source.is_absolute() or not target.is_absolute() or source.resolve() == target.resolve():
        raise ValueError("Se requieren dos rutas absolutas distintas")
    policy = adaptive_policy(POLICY, minimum_minutes, maximum_minutes)
    # Reservar el destino sin sobrescribir archivos existentes.
    target.open("xb").close()
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
            original.execute("BEGIN")
            state = _stored_state(original)
            if original.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("La base de origen no supera quick_check")
            with closing(sqlite3.connect(target)) as destination:
                original.backup(destination)
                state["policy"] = policy
                state["policy_migrations"] = [{
                    "from": POLICY["version"], "to": policy["version"],
                    "migrated_at": datetime.now(timezone.utc).isoformat(),
                    "legacy_offers_cooldown_minutes": POLICY["cooldown_minutes"],
                }]
                destination.execute("UPDATE state SET body=? WHERE id=1", (_json(state),))
                destination.commit()
        candidate = ChildOfferCoordinator(target, policy=policy)
        with closing(sqlite3.connect(target)) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("La copia no supera quick_check")
        return {"status": "copied", "policy": candidate.policy,
                "legacy_receipts_preserved": state["receipt_count"],
                "source_modified": False}
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--pmum-min-minutes", type=int, required=True)
    parser.add_argument("--pmum-max-minutes", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.source, args.target, args.pmum_min_minutes, args.pmum_max_minutes)))


if __name__ == "__main__":
    main()
