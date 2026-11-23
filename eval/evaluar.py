"""Atajo para correr la evaluación sin instalar el paquete.

    python eval/evaluar.py                          # 12 tareas, con y sin skills
    python eval/evaluar.py --tareas S1,M1,C1        # solo algunas
    python eval/evaluar.py --pausa 10               # más espera si aparece el error 429

La lógica está en src/lupa/evaluacion.py y las tareas en eval/tareas.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lupa.evaluacion import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
