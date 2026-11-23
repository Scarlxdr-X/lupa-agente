"""Tool `ejecutar_python`: corre código pandas/matplotlib escrito por el LLM.

Medidas de seguridad (proporcionales a un proyecto académico):
    - El código corre en un proceso aparte, nunca dentro del agente.
    - Tiene tiempo límite (60 s por defecto).
    - Corre dentro de la carpeta de trabajo de la sesión.
    - Se rechazan operaciones que no tienen nada que ver con analizar datos
      (borrar archivos, lanzar comandos del sistema, abrir conexiones).
Si el código falla, el error vuelve al LLM para que lo corrija.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap

from ..llm.base import DefinicionTool
from .base import Contexto, ErrorTool, Tool

PREAMBULO = textwrap.dedent(
    """\
    import matplotlib
    matplotlib.use("Agg")  # sin ventana: las gráficas se guardan en archivos
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    """
)

PROHIBIDO = re.compile(
    r"\b(subprocess|os\.system|os\.popen|os\.remove|os\.unlink|os\.rmdir|shutil|socket|requests|urllib"
    r"|http\.client|eval\(|exec\(|__import__|open\([^)]*['\"][wa]\+?['\"])"
)

DEF_EJECUTAR = DefinicionTool(
    nombre="ejecutar_python",
    descripcion=(
        "Ejecuta código Python en la carpeta de trabajo, con pandas (pd), numpy (np) y matplotlib.pyplot (plt) "
        "ya importados. Las tablas de consultar_dataset están ahí como CSV: pd.read_csv('tabla_1.csv'). "
        "Cada ejecución empieza de cero (no recuerda variables anteriores). Usa print() para ver resultados. "
        "Para gráficas: plt.savefig('nombre.png', dpi=120, bbox_inches='tight'); siempre con título, ejes "
        "con unidades y la fuente en el pie. No puede acceder a internet ni borrar archivos."
    ),
    parametros={
        "type": "object",
        "properties": {"codigo": {"type": "string", "description": "Código Python a ejecutar."}},
        "required": ["codigo"],
    },
)


def ejecutar_python(contexto: Contexto, codigo: str, timeout_s: float = 60) -> str:
    prohibido = PROHIBIDO.search(codigo)
    if prohibido:
        raise ErrorTool(
            f"El código usa '{prohibido.group(0)}', que no está permitido. Esta tool es solo para analizar "
            "las tablas y hacer gráficas."
        )

    n = len(list(contexto.carpeta.glob("paso_*.py"))) + 1
    archivo = contexto.carpeta / f"paso_{n}.py"
    archivo.write_text(PREAMBULO + "\n" + codigo, encoding="utf-8")
    imagenes_antes = {p.name: p.stat().st_mtime for p in contexto.carpeta.glob("*.png")}

    entorno = {**os.environ, "MPLBACKEND": "Agg", "PYTHONIOENCODING": "utf-8"}
    try:
        proceso = subprocess.run(
            [sys.executable, archivo.name],
            cwd=contexto.carpeta,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=entorno,
        )
    except subprocess.TimeoutExpired as exc:
        raise ErrorTool(f"El código tardó más de {timeout_s:.0f} s y se detuvo. Simplifícalo.") from exc

    nuevas = sorted(
        p for p in contexto.carpeta.glob("*.png") if imagenes_antes.get(p.name) != p.stat().st_mtime
    )
    for img in nuevas:
        if img not in contexto.graficas:
            contexto.graficas.append(img)

    salida = (proceso.stdout or "").strip()
    errores = _limpiar_traceback(proceso.stderr or "", archivo.name)
    partes = []
    if proceso.returncode != 0:
        partes.append(f"ERROR al ejecutar (código {proceso.returncode}):\n{errores[-2500:]}")
    if salida:
        partes.append(f"Salida:\n{salida[-5000:]}")
    if nuevas:
        partes.append("Gráficas guardadas: " + ", ".join(p.name for p in nuevas))
    if not partes:
        partes.append("El código se ejecutó sin errores pero no imprimió nada. Usa print() para ver resultados.")
    if proceso.returncode != 0:
        raise ErrorTool("\n".join(partes))
    return "\n".join(partes)


def _limpiar_traceback(stderr: str, nombre_archivo: str) -> str:
    """Deja solo lo útil del error y corrige los números de línea por el preámbulo."""
    lineas_preambulo = PREAMBULO.count("\n") + 1

    def corregir(m: re.Match) -> str:
        return f'"{nombre_archivo}", line {max(1, int(m.group(1)) - lineas_preambulo)}'

    texto = re.sub(rf'"[^"]*{re.escape(nombre_archivo)}", line (\d+)', corregir, stderr)
    # Las advertencias de librerías no ayudan al LLM
    return "\n".join(linea for linea in texto.splitlines() if "Warning" not in linea or "Error" in linea).strip()


def tool_ejecutar_python(contexto: Contexto, timeout_s: float = 60) -> Tool:
    def funcion(codigo: str) -> str:
        return ejecutar_python(contexto, codigo, timeout_s)

    return Tool(DEF_EJECUTAR, funcion)
