"""Reemplaza el marcador USUARIO por el usuario de GitHub del equipo.

    python scripts/poner_usuario.py nombre-de-usuario

Toca el README y los notebooks, que traen enlaces al repositorio.
Funciona igual en Windows, Mac y Linux.
"""

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS = [RAIZ / "README.md", *sorted((RAIZ / "notebooks").glob("*.ipynb"))]


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", sys.argv[1]):
        print("Uso: python scripts/poner_usuario.py nombre-de-usuario-de-github")
        return 1
    usuario = sys.argv[1]
    for archivo in ARCHIVOS:
        texto = archivo.read_text(encoding="utf-8")
        cambios = texto.count("USUARIO")
        if cambios:
            archivo.write_text(texto.replace("USUARIO", usuario), encoding="utf-8")
            print(f"{archivo.relative_to(RAIZ)}: {cambios} reemplazos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
