"""Carga retroativa do historico estruturado de etapas.

Uso: .venv/Scripts/python -m backend.scripts.carga_etapas --empresa 2 [--aplicar]
Sem --aplicar apenas simula e imprime as contagens.
"""

import argparse

from ..database import SessionLocal
from ..services import etapa_historico


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empresa", type=int, required=True)
    parser.add_argument("--aplicar", action="store_true", help="grava (padrao: simulacao)")
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        resultado = etapa_historico.carga_retroativa(db, args.empresa, aplicar=args.aplicar)
    print("APLICADO" if args.aplicar else "SIMULACAO", resultado)
    return resultado


if __name__ == "__main__":
    main()
