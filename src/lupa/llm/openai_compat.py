"""Proveedor para APIs compatibles con OpenAI (Chat Completions).

Lo usamos con Groq como respaldo de Gemini, pero sirve igual para OpenAI,
OpenRouter u Ollama local: solo cambian `base_url`, la clave y el modelo.
"""

from __future__ import annotations

import json
from typing import Any

import openai
from openai import OpenAI

from .base import (
    DefinicionTool,
    ErrorConfiguracion,
    LlamadaTool,
    Mensaje,
    ProveedorLLM,
    RespuestaLLM,
    Uso,
    nuevo_id_llamada,
)

_ERRORES_TEMPORALES = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


class ProveedorOpenAICompat(ProveedorLLM):
    nombre = "openai_compat"

    def __init__(
        self,
        api_key: str | None,
        modelo: str = "openai/gpt-oss-120b",
        base_url: str = "https://api.groq.com/openai/v1",
        cliente: OpenAI | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(modelo, **kwargs)
        if cliente is None:
            if not api_key:
                raise ErrorConfiguracion(
                    "Falta GROQ_API_KEY (o LUPA_OPENAI_API_KEY). Para Groq créala en "
                    "https://console.groq.com/keys y guárdala en el .env o en los secretos de Colab."
                )
            # max_retries=0: los reintentos los maneja ProveedorLLM.generar
            cliente = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)
        self.cliente = cliente
        self.base_url = base_url

    # -- llamada a la API ----------------------------------------------------

    def _generar(
        self, mensajes: list[Mensaje], tools: list[DefinicionTool], sistema: str | None
    ) -> RespuestaLLM:
        parametros: dict[str, Any] = {"model": self.modelo, "messages": self.a_mensajes(mensajes, sistema)}
        if tools:
            parametros["tools"] = self.a_tools(tools)
        respuesta = self.cliente.chat.completions.create(**parametros)
        return self.desde_respuesta(respuesta)

    def _es_reintentable(self, error: Exception) -> bool:
        return isinstance(error, _ERRORES_TEMPORALES)

    # -- traducción: formato de Lupa → formato OpenAI -----------------------

    @staticmethod
    def a_tools(tools: list[DefinicionTool]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {"name": t.nombre, "description": t.descripcion, "parameters": t.parametros},
            }
            for t in tools
        ]

    @staticmethod
    def a_mensajes(mensajes: list[Mensaje], sistema: str | None) -> list[dict[str, Any]]:
        salida: list[dict[str, Any]] = []
        if sistema:
            salida.append({"role": "system", "content": sistema})
        for m in mensajes:
            if m.rol == "usuario":
                salida.append({"role": "user", "content": m.texto})
            elif m.rol == "asistente":
                item: dict[str, Any] = {"role": "assistant", "content": m.texto or None}
                if m.llamadas:
                    item["tool_calls"] = [
                        {
                            "id": ll.id,
                            "type": "function",
                            "function": {
                                "name": ll.nombre,
                                "arguments": json.dumps(ll.argumentos, ensure_ascii=False),
                            },
                        }
                        for ll in m.llamadas
                    ]
                salida.append(item)
            elif m.rol == "tool":
                salida.append({"role": "tool", "tool_call_id": m.id_llamada, "content": m.texto})
            else:  # pragma: no cover
                raise ValueError(f"Rol desconocido: {m.rol}")
        return salida

    # -- traducción: respuesta OpenAI → formato de Lupa ---------------------

    def desde_respuesta(self, respuesta: Any) -> RespuestaLLM:
        eleccion = respuesta.choices[0]
        msg = eleccion.message

        llamadas = []
        for tc in msg.tool_calls or []:
            llamadas.append(
                LlamadaTool(
                    id=tc.id or nuevo_id_llamada(),
                    nombre=tc.function.name,
                    argumentos=_leer_argumentos(tc.function.arguments),
                )
            )

        uso = Uso()
        if getattr(respuesta, "usage", None):
            uso = Uso(
                tokens_entrada=respuesta.usage.prompt_tokens or 0,
                tokens_salida=respuesta.usage.completion_tokens or 0,
            )

        return RespuestaLLM(
            mensaje=Mensaje(
                rol="asistente", texto=msg.content or "", llamadas=llamadas, nativo=msg, proveedor=self.nombre
            ),
            uso=uso,
            motivo_fin=eleccion.finish_reason,
        )


def _leer_argumentos(crudo: str | None) -> dict[str, Any]:
    """Los argumentos llegan como texto JSON. Si el modelo envía JSON inválido,
    se devuelve una marca de error para que el agente se lo informe al LLM."""
    if not crudo:
        return {}
    try:
        valor = json.loads(crudo)
    except json.JSONDecodeError:
        return {"_error_argumentos": f"JSON inválido: {crudo[:200]}"}
    return valor if isinstance(valor, dict) else {"_error_argumentos": f"Se esperaba un objeto JSON: {crudo[:200]}"}
