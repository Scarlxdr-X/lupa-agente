"""Tool `calculadora`: evalúa expresiones aritméticas de forma exacta y segura.

Los LLM se equivocan en cuentas con muchos dígitos. Esta tool las resuelve sin
usar `eval` de Python (que ejecutaría cualquier código): recorre el árbol
sintáctico de la expresión y solo acepta números, operadores y unas pocas
funciones matemáticas.
"""

from __future__ import annotations

import ast
import math
import operator

from ..llm.base import DefinicionTool
from .base import ErrorTool, Tool

_OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARIOS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCIONES = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
}
_CONSTANTES = {"pi": math.pi, "e": math.e}

DEF_CALCULADORA = DefinicionTool(
    nombre="calculadora",
    descripcion=(
        "Evalúa una expresión aritmética exacta: + - * / // % ** y paréntesis, con abs, round, min, max, sqrt, "
        "log, log10 y exp. Úsala para cualquier cuenta (diferencias, porcentajes, conversiones) en vez de "
        "calcular de memoria. Ejemplo: '(3706.97 - 4409.15) * 1000'. Usa punto decimal, sin separadores de miles."
    ),
    parametros={
        "type": "object",
        "properties": {"expresion": {"type": "string", "description": "Expresión a evaluar."}},
        "required": ["expresion"],
    },
)


def evaluar(expresion: str, variables: dict[str, float] | None = None) -> float:
    """Evalúa la expresión. `variables` permite nombres extra (lo usa la evaluación)."""
    nombres = {**_CONSTANTES, **(variables or {})}
    try:
        arbol = ast.parse(expresion.strip(), mode="eval")
    except SyntaxError as exc:
        raise ErrorTool(f"La expresión no es válida: {exc.msg}. Usa punto decimal y sin separadores de miles.") from exc
    return _evaluar_nodo(arbol.body, nombres)


def _evaluar_nodo(nodo: ast.AST, nombres: dict[str, float]) -> float:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)) and not isinstance(nodo.value, bool):
        return nodo.value
    if isinstance(nodo, ast.Name) and nodo.id in nombres:
        return nombres[nodo.id]
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        izq, der = _evaluar_nodo(nodo.left, nombres), _evaluar_nodo(nodo.right, nombres)
        if isinstance(nodo.op, ast.Pow) and abs(der) > 1000:
            raise ErrorTool("Exponente demasiado grande.")
        try:
            return _OPERADORES[type(nodo.op)](izq, der)
        except ZeroDivisionError as exc:
            raise ErrorTool("División por cero.") from exc
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _UNARIOS:
        return _UNARIOS[type(nodo.op)](_evaluar_nodo(nodo.operand, nombres))
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in _FUNCIONES:
        argumentos = [_evaluar_nodo(a, nombres) for a in nodo.args]
        try:
            return _FUNCIONES[nodo.func.id](*argumentos)
        except (TypeError, ValueError) as exc:
            raise ErrorTool(f"Error en {nodo.func.id}: {exc}") from exc
    raise ErrorTool(f"Elemento no permitido en la expresión: {ast.dump(nodo)[:80]}")


def formatear(valor: float) -> str:
    """'-702180.0' -> '-702180 (≈ -702.180)': valor exacto + versión legible con miles."""
    if isinstance(valor, float) and valor.is_integer() and abs(valor) < 1e15:
        valor = int(valor)
    exacto = f"{valor:.10g}" if isinstance(valor, float) else str(valor)
    legible = f"{valor:,.2f}" if isinstance(valor, float) else f"{valor:,}"
    legible = legible.replace(",", "_").replace(".", ",").replace("_", ".")  # formato colombiano
    return f"{exacto} (en formato colombiano: {legible})"


def calculadora(expresion: str) -> str:
    return f"{expresion} = {formatear(evaluar(expresion))}"


def tool_calculadora() -> Tool:
    return Tool(DEF_CALCULADORA, calculadora)
