"""Piezas comunes de las tools: contexto compartido, registro y ejecución segura.

Una tool es una función de Python + su `DefinicionTool` (lo que ve el LLM).
El `RegistroTools` recibe las llamadas del LLM, valida los argumentos, ejecuta
la función y devuelve SIEMPRE texto: si algo falla, el error también es texto,
para que el LLM lo lea y corrija su siguiente intento en vez de romper el ciclo.
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..llm.base import DefinicionTool, LlamadaTool

#: Máximo de caracteres que una tool le devuelve al LLM (cuida el contexto y la cuota).
MAX_CARACTERES_RESULTADO = 8000


class ErrorTool(Exception):
    """Error esperado de una tool (consulta inválida, falta una clave...).
    Su mensaje se le muestra al LLM tal cual, así que debe decir cómo corregirlo."""


@dataclass
class Fuente:
    """Un conjunto de datos o una página web que el agente consultó."""

    tipo: str  # "dataset" o "web"
    titulo: str
    url: str


@dataclass
class Contexto:
    """Estado compartido por las tools durante una sesión del agente.

    - `carpeta`: carpeta de trabajo. Ahí quedan las tablas consultadas
      (tabla_1.csv, ...) y las gráficas, para que `ejecutar_python` las use.
    - `fuentes`: lo que se consultó, para citarlo en el informe.
    """

    carpeta: Path
    fuentes: list[Fuente] = field(default_factory=list)
    graficas: list[Path] = field(default_factory=list)
    tablas: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.carpeta = Path(self.carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def nombre_nueva_tabla(self) -> str:
        nombre = f"tabla_{len(self.tablas) + 1}.csv"
        self.tablas.append(nombre)
        return nombre

    def agregar_fuente(self, fuente: Fuente) -> None:
        if all(f.url != fuente.url for f in self.fuentes):
            self.fuentes.append(fuente)


@dataclass
class Tool:
    definicion: DefinicionTool
    funcion: Callable[..., str]

    @property
    def nombre(self) -> str:
        return self.definicion.nombre


@dataclass
class ResultadoTool:
    texto: str
    ok: bool
    duracion_s: float


class RegistroTools:
    """Conjunto de tools disponibles para el agente."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {t.nombre: t for t in tools}

    @property
    def nombres(self) -> list[str]:
        return list(self._tools)

    @property
    def definiciones(self) -> list[DefinicionTool]:
        return [t.definicion for t in self._tools.values()]

    def __contains__(self, nombre: str) -> bool:
        return nombre in self._tools

    def ejecutar(self, llamada: LlamadaTool) -> ResultadoTool:
        inicio = time.perf_counter()
        try:
            texto = self._ejecutar(llamada)
            ok = True
        except ErrorTool as exc:
            texto, ok = f"ERROR: {exc}", False
        except Exception as exc:  # noqa: BLE001 - cualquier fallo vuelve al LLM como texto
            texto, ok = f"ERROR inesperado en {llamada.nombre} ({type(exc).__name__}): {exc}", False
        if len(texto) > MAX_CARACTERES_RESULTADO:
            texto = texto[:MAX_CARACTERES_RESULTADO] + "\n[... resultado recortado ...]"
        return ResultadoTool(texto=texto, ok=ok, duracion_s=time.perf_counter() - inicio)

    def _ejecutar(self, llamada: LlamadaTool) -> str:
        tool = self._tools.get(llamada.nombre)
        if tool is None:
            raise ErrorTool(f"No existe la tool '{llamada.nombre}'. Las disponibles son: {', '.join(self.nombres)}")

        argumentos = dict(llamada.argumentos)
        if "_error_argumentos" in argumentos:
            raise ErrorTool(f"Los argumentos no son JSON válido: {argumentos['_error_argumentos']}")

        requeridos = llamada_requeridos(tool.definicion)
        faltan = [r for r in requeridos if argumentos.get(r) in (None, "")]
        if faltan:
            raise ErrorTool(f"Faltan argumentos obligatorios: {', '.join(faltan)}")

        # Ignora argumentos que la función no acepta (el LLM a veces inventa alguno)
        aceptados = inspect.signature(tool.funcion).parameters
        argumentos = {k: v for k, v in argumentos.items() if k in aceptados}
        return tool.funcion(**argumentos)


def llamada_requeridos(definicion: DefinicionTool) -> list[str]:
    return list(definicion.parametros.get("required", []))


def entero(valor: Any, defecto: int, minimo: int, maximo: int) -> int:
    """Convierte a entero dentro de [minimo, maximo]. El LLM a veces manda "5" o 5.0."""
    try:
        n = int(float(valor))
    except (TypeError, ValueError):
        n = defecto
    return max(minimo, min(maximo, n))
