"""Capa de LLM: una interfaz común y un proveedor por servicio.

Uso típico:
    from lupa.config import Config
    from lupa.llm import crear_proveedor, Mensaje

    llm = crear_proveedor(Config.cargar())
    respuesta = llm.generar([Mensaje.usuario("Hola")])
    print(respuesta.texto)
"""

from __future__ import annotations

from ..config import Config
from .base import (
    DefinicionTool,
    ErrorConfiguracion,
    ErrorLLM,
    LlamadaTool,
    Mensaje,
    ProveedorLLM,
    RespuestaLLM,
    Uso,
)

__all__ = [
    "DefinicionTool",
    "ErrorConfiguracion",
    "ErrorLLM",
    "LlamadaTool",
    "Mensaje",
    "ProveedorLLM",
    "RespuestaLLM",
    "Uso",
    "crear_proveedor",
]


def crear_proveedor(config: Config | None = None, nombre: str | None = None) -> ProveedorLLM:
    """Crea el proveedor indicado por `nombre` o, si no se da, por LUPA_PROVEEDOR.

    Los imports van dentro de la función para que, por ejemplo, quien solo use
    Groq no necesite cargar el SDK de Gemini.
    """
    config = config or Config.cargar()
    nombre = (nombre or config.proveedor).lower()

    if nombre == "gemini":
        from .gemini import ProveedorGemini

        return ProveedorGemini(api_key=config.gemini_api_key, modelo=config.modelo_gemini)
    if nombre == "openai_compat":
        from .openai_compat import ProveedorOpenAICompat

        return ProveedorOpenAICompat(
            api_key=config.openai_api_key, modelo=config.modelo_openai, base_url=config.openai_base_url
        )
    raise ErrorConfiguracion(f"Proveedor desconocido: '{nombre}'. Usa 'gemini' u 'openai_compat'.")
