"""Utilidades compartidas por las pruebas. Ninguna prueba llama a una API real."""

from __future__ import annotations

import pytest

from lupa.llm.base import DefinicionTool, ProveedorLLM, RespuestaLLM

VARIABLES_LUPA = [
    "LUPA_PROVEEDOR",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "LUPA_MODELO_GEMINI",
    "GROQ_API_KEY",
    "LUPA_OPENAI_API_KEY",
    "LUPA_OPENAI_BASE_URL",
    "LUPA_MODELO_OPENAI",
    "TAVILY_API_KEY",
    "SODA_APP_TOKEN",
    "LUPA_MAX_PASOS",
]


@pytest.fixture
def entorno_limpio(monkeypatch, tmp_path):
    """Borra las variables de Lupa y trabaja en una carpeta sin .env."""
    for nombre in VARIABLES_LUPA:
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.chdir(tmp_path)
    return monkeypatch


TOOL_EJEMPLO = DefinicionTool(
    nombre="buscar_datasets",
    descripcion="Busca conjuntos de datos en datos.gov.co",
    parametros={
        "type": "object",
        "properties": {"consulta": {"type": "string"}},
        "required": ["consulta"],
    },
)


class ProveedorGuionado(ProveedorLLM):
    """Proveedor falso que devuelve respuestas preparadas, en orden."""

    nombre = "guionado"

    def __init__(self, respuestas: list[RespuestaLLM]):
        super().__init__(modelo="falso", max_reintentos=0)
        self.respuestas = list(respuestas)
        self.llamadas_recibidas: list[dict] = []

    def _generar(self, mensajes, tools, sistema):
        self.llamadas_recibidas.append({"mensajes": list(mensajes), "tools": tools, "sistema": sistema})
        return self.respuestas.pop(0)

    def _es_reintentable(self, error):
        return False
