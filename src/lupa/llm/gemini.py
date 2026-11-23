"""Proveedor para los modelos Gemini, usando el SDK oficial `google-genai`.

Detalles que este módulo resuelve:
    - Desactiva el "function calling automático" del SDK: queremos que el ciclo
      del agente (fase 3) ejecute las tools, no el SDK.
    - Gemini 3 devuelve "firmas de pensamiento" en las llamadas a tools y exige
      recibirlas de vuelta en el siguiente turno (si no, error 400). Por eso
      cada respuesta guarda su `Content` original en `Mensaje.nativo` y se
      reenvía sin modificar.
    - Si el LLM pide varias tools a la vez, todos los resultados deben ir en un
      mismo `Content`; intercalarlos también produce error 400.
"""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors, types

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

# Códigos HTTP que indican un problema temporal: límite de peticiones o servidor.
_CODIGOS_TEMPORALES = {429, 500, 502, 503, 504}


class ProveedorGemini(ProveedorLLM):
    nombre = "gemini"

    def __init__(
        self,
        api_key: str | None,
        modelo: str = "gemini-3.7-flash",
        cliente: genai.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(modelo, **kwargs)
        if cliente is None:
            if not api_key:
                raise ErrorConfiguracion(
                    "Falta GEMINI_API_KEY. Créala en https://aistudio.google.com/apikey "
                    "y guárdala en el .env o en los secretos de Colab."
                )
            cliente = genai.Client(api_key=api_key)
        self.cliente = cliente

    # -- llamada a la API ----------------------------------------------------

    def _generar(
        self, mensajes: list[Mensaje], tools: list[DefinicionTool], sistema: str | None
    ) -> RespuestaLLM:
        config = types.GenerateContentConfig(
            system_instruction=sistema,
            tools=[self._a_tool(tools)] if tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        respuesta = self.cliente.models.generate_content(
            model=self.modelo,
            contents=self.a_contents(mensajes),
            config=config,
        )
        return self.desde_respuesta(respuesta)

    def _es_reintentable(self, error: Exception) -> bool:
        return isinstance(error, errors.APIError) and error.code in _CODIGOS_TEMPORALES

    def listar_modelos(self) -> list[str]:
        """Modelos que la clave puede usar para generar texto."""
        nombres = []
        for modelo in self.cliente.models.list():
            acciones = getattr(modelo, "supported_actions", None) or []
            if not acciones or "generateContent" in acciones:
                nombres.append(modelo.name.removeprefix("models/"))
        return sorted(nombres)

    # -- traducción: formato de Lupa → formato de Gemini --------------------

    @staticmethod
    def _a_tool(tools: list[DefinicionTool]) -> types.Tool:
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t.nombre,
                    description=t.descripcion,
                    parameters_json_schema=t.parametros,
                )
                for t in tools
            ]
        )

    def a_contents(self, mensajes: list[Mensaje]) -> list[types.Content]:
        """Convierte el historial de Lupa en la lista `contents` de Gemini."""
        contents: list[types.Content] = []
        resultados_pendientes: list[types.Part] = []

        def volcar_resultados() -> None:
            # Los resultados consecutivos de tools van juntos en un solo Content.
            if resultados_pendientes:
                contents.append(types.Content(role="user", parts=list(resultados_pendientes)))
                resultados_pendientes.clear()

        for m in mensajes:
            if m.rol == "tool":
                resultados_pendientes.append(self._parte_resultado(m))
                continue

            volcar_resultados()
            if m.rol == "usuario":
                contents.append(types.Content(role="user", parts=[types.Part(text=m.texto)]))
            elif m.rol == "asistente":
                contents.append(self._content_asistente(m))
            else:  # pragma: no cover - el tipo Rol no permite otros valores
                raise ValueError(f"Rol desconocido: {m.rol}")

        volcar_resultados()
        return contents

    def _content_asistente(self, m: Mensaje) -> types.Content:
        # Caso normal: reenviar exactamente lo que devolvió Gemini (con firmas).
        if m.proveedor == self.nombre and isinstance(m.nativo, types.Content):
            return m.nativo
        # Mensaje de otro proveedor: se reconstruye. Sirve para texto; con
        # llamadas a tools, Gemini 3 puede rechazarlo por faltar las firmas.
        partes: list[types.Part] = []
        if m.texto:
            partes.append(types.Part(text=m.texto))
        for llamada in m.llamadas:
            partes.append(
                types.Part(
                    function_call=types.FunctionCall(
                        id=_id_para_api(llamada.id), name=llamada.nombre, args=llamada.argumentos
                    )
                )
            )
        return types.Content(role="model", parts=partes or [types.Part(text="")])

    @staticmethod
    def _parte_resultado(m: Mensaje) -> types.Part:
        return types.Part(
            function_response=types.FunctionResponse(
                id=_id_para_api(m.id_llamada),
                name=m.nombre_tool,
                response={"resultado": m.texto},
            )
        )

    # -- traducción: respuesta de Gemini → formato de Lupa ------------------

    def desde_respuesta(self, respuesta: types.GenerateContentResponse) -> RespuestaLLM:
        candidato = respuesta.candidates[0] if respuesta.candidates else None
        content = candidato.content if candidato else None
        partes = (content.parts if content else None) or []

        # El texto visible excluye los "pensamientos" (partes con thought=True).
        texto = "".join(p.text for p in partes if p.text and not p.thought)
        llamadas = [
            LlamadaTool(id=fc.id or nuevo_id_llamada(), nombre=fc.name or "", argumentos=dict(fc.args or {}))
            for fc in (respuesta.function_calls or [])
        ]

        meta = respuesta.usage_metadata
        uso = Uso(
            tokens_entrada=(meta.prompt_token_count or 0) if meta else 0,
            # Los tokens de pensamiento se cobran como salida.
            tokens_salida=((meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)) if meta else 0,
        )
        motivo = None
        if candidato and candidato.finish_reason is not None:
            motivo = getattr(candidato.finish_reason, "value", str(candidato.finish_reason))

        return RespuestaLLM(
            mensaje=Mensaje(rol="asistente", texto=texto, llamadas=llamadas, nativo=content, proveedor=self.nombre),
            uso=uso,
            motivo_fin=motivo,
        )


def _id_para_api(id_llamada: str | None) -> str | None:
    """Los ids generados por Lupa (prefijo `lupa-`) no se envían a Gemini."""
    if not id_llamada or id_llamada.startswith("lupa-"):
        return None
    return id_llamada
