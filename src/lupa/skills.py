"""Skills: procedimientos escritos que le enseñan al agente a resolver un tipo de tarea.

Cada skill es una carpeta `skills/<nombre>/SKILL.md` con:
    - Un encabezado YAML: nombre, descripción (una línea) y tools que usa.
    - El procedimiento en markdown: pasos, reglas, errores comunes, ejemplos.

Carga progresiva: el prompt del agente solo lleva el nombre y la descripción
de cada skill. Cuando el agente decide que necesita uno, llama a la tool
`cargar_skill` y recibe el procedimiento completo. Así el contexto se mantiene
corto y los skills se pueden editar sin tocar el código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from .llm.base import DefinicionTool
from .tools.base import ErrorTool, Tool


@dataclass
class Skill:
    nombre: str
    descripcion: str
    instrucciones: str
    tools: list[str] = field(default_factory=list)
    ruta: Path | None = None


def carpeta_skills_por_defecto() -> Path:
    """`LUPA_CARPETA_SKILLS` o la carpeta skills/ en la raíz del repositorio."""
    if os.environ.get("LUPA_CARPETA_SKILLS"):
        return Path(os.environ["LUPA_CARPETA_SKILLS"])
    raiz_repo = Path(__file__).resolve().parents[2]  # src/lupa/skills.py -> raíz
    if (raiz_repo / "skills").is_dir():
        return raiz_repo / "skills"
    return Path.cwd() / "skills"


def leer_skill(archivo: Path) -> Skill:
    texto = archivo.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        raise ValueError(f"{archivo} no empieza con un encabezado YAML (---)")
    _, encabezado, cuerpo = texto.split("---", 2)
    meta = yaml.safe_load(encabezado) or {}
    for clave in ("nombre", "descripcion"):
        if not meta.get(clave):
            raise ValueError(f"{archivo}: falta '{clave}' en el encabezado")
    return Skill(
        nombre=str(meta["nombre"]),
        descripcion=" ".join(str(meta["descripcion"]).split()),
        instrucciones=cuerpo.strip(),
        tools=list(meta.get("tools") or []),
        ruta=archivo,
    )


def cargar_skills(carpeta: Path | None = None) -> dict[str, Skill]:
    carpeta = Path(carpeta) if carpeta else carpeta_skills_por_defecto()
    skills = {}
    for archivo in sorted(carpeta.glob("*/SKILL.md")):
        skill = leer_skill(archivo)
        skills[skill.nombre] = skill
    return skills


def catalogo(skills: dict[str, Skill]) -> str:
    """Lista corta para el prompt de sistema: una línea por skill."""
    return "\n".join(f"- {s.nombre}: {s.descripcion}" for s in skills.values())


def tool_cargar_skill(skills: dict[str, Skill], al_cargar: Callable[[str], None] | None = None) -> Tool:
    """Tool que devuelve el procedimiento completo de un skill."""
    definicion = DefinicionTool(
        nombre="cargar_skill",
        descripcion=(
            "Carga el procedimiento completo de un skill (pasos, reglas, datos verificados y errores comunes). "
            "Cárgalo ANTES de empezar la parte de la tarea que cubre y síguelo. Skills: " + ", ".join(skills)
        ),
        parametros={
            "type": "object",
            "properties": {"nombre": {"type": "string", "enum": list(skills), "description": "Nombre del skill."}},
            "required": ["nombre"],
        },
    )

    def funcion(nombre: str) -> str:
        skill = skills.get(nombre.strip())
        if skill is None:
            raise ErrorTool(f"No existe el skill '{nombre}'. Disponibles: {', '.join(skills)}")
        if al_cargar:
            al_cargar(skill.nombre)
        tools = f"Tools de este skill: {', '.join(skill.tools)}\n\n" if skill.tools else ""
        return f"# Skill: {skill.nombre}\n{tools}{skill.instrucciones}"

    return Tool(definicion, funcion)
