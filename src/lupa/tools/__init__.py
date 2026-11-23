"""Tools del agente.

    buscar_datasets     catálogo de datos.gov.co
    consultar_dataset   API SODA de datos.gov.co (consultas SoQL)
    ejecutar_python     pandas y matplotlib en un proceso aparte
    buscar_web          Tavily
    calculadora         expresiones aritméticas exactas, sin eval
    cargar_skill        procedimiento completo de un skill (ver lupa/skills.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from ..config import Config
from .base import Contexto, ErrorTool, Fuente, RegistroTools, ResultadoTool, Tool
from .calculadora import tool_calculadora
from .datos_gov import ClienteSODA, tool_buscar_datasets, tool_consultar_dataset
from .python_exec import tool_ejecutar_python
from .web import tool_buscar_web

if TYPE_CHECKING:
    from ..skills import Skill

__all__ = [
    "ClienteSODA",
    "Contexto",
    "ErrorTool",
    "Fuente",
    "RegistroTools",
    "ResultadoTool",
    "Tool",
    "crear_registro",
]


def crear_registro(
    config: Config,
    contexto: Contexto,
    skills: dict[str, "Skill"] | None = None,
    cliente_soda: ClienteSODA | None = None,
    al_cargar_skill: Callable[[str], None] | None = None,
) -> RegistroTools:
    """Arma el registro de tools. Si `skills` es None o vacío, no se incluye
    `cargar_skill` (es la configuración "sin skills" de la evaluación)."""
    cliente_soda = cliente_soda or ClienteSODA(
        app_token=config.soda_app_token,
        carpeta_cache=Path(config.carpeta_cache) / "datos_gov",
        horas_cache=config.horas_cache,
    )
    tools = [
        tool_buscar_datasets(cliente_soda),
        tool_consultar_dataset(cliente_soda, contexto),
        tool_ejecutar_python(contexto),
        tool_buscar_web(config.tavily_api_key, contexto),
        tool_calculadora(),
    ]
    if skills:
        from ..skills import tool_cargar_skill

        tools.append(tool_cargar_skill(skills, al_cargar_skill))
    return RegistroTools(tools)
