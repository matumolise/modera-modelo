"""Inicialización explícita del almacén, separada del arranque del servidor."""

import argparse
from pathlib import Path

from .child_offers import ChildOfferCoordinator
from .child_offer_timing import adaptive_policy
from .child_offers import POLICY


def main():
    parser = argparse.ArgumentParser(description="Inicializar o validar una base del coordinador")
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--pmum-min-minutes", type=int)
    parser.add_argument("--pmum-max-minutes", type=int)
    args = parser.parse_args()
    if not args.path.is_absolute():
        parser.error("La ruta debe ser absoluta")
    existed = args.path.exists()
    policy = POLICY
    if args.pmum_min_minutes is not None or args.pmum_max_minutes is not None:
        policy = adaptive_policy(POLICY, args.pmum_min_minutes, args.pmum_max_minutes)
    ChildOfferCoordinator(args.path, create=True, policy=policy)
    print("Base existente validada sin reiniciar el estado" if existed else "Base nueva inicializada explícitamente")


if __name__ == "__main__":
    main()
