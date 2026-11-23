"""Atajo para verificar la conexión con los LLM sin instalar el paquete.

    python scripts/verificar_conexion.py                  # proveedor de LUPA_PROVEEDOR
    python scripts/verificar_conexion.py --proveedor todos
    python scripts/verificar_conexion.py --listar-modelos

La lógica está en src/lupa/verificacion.py.
"""

import sys
from pathlib import Path

# Permite ejecutar el script sin `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lupa.verificacion import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
