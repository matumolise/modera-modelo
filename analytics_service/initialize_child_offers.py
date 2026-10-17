"""Inicialización explícita del almacén, separada del arranque del servidor."""

import argparse
from pathlib import Path

from .child_offers import ChildOfferCoordinator


def main():
    parser = argparse.ArgumentParser(description="Inicializar o validar una base del coordinador")
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()
    if not args.path.is_absolute():
        parser.error("La ruta debe ser absoluta")
    existed = args.path.exists()
    ChildOfferCoordinator(args.path, create=True)
    print("Base existente validada sin reiniciar el estado" if existed else "Base nueva inicializada explícitamente")


if __name__ == "__main__":
    main()
